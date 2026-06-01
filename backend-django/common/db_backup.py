from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from django.conf import settings


BASE_DIR = Path(__file__).resolve().parents[1]


class DatabaseBackupError(RuntimeError):
    pass


@dataclass(frozen=True)
class MySQLBackupResult:
    path: Path
    database: str
    size_bytes: int
    command: tuple[str, ...]


def backup_mysql_database(
    output_dir: str | os.PathLike[str] | None = None,
    database: str = "default",
) -> MySQLBackupResult:
    db_config = settings.DATABASES.get(database)
    if not db_config:
        raise DatabaseBackupError(f"未找到数据库配置: {database}")

    engine = str(db_config.get("ENGINE", "")).lower()
    if "mysql" not in engine:
        raise DatabaseBackupError(f"当前备份任务仅支持 MySQL，实际数据库引擎为: {db_config.get('ENGINE')}")

    db_name = str(db_config.get("NAME") or "").strip()
    if not db_name:
        raise DatabaseBackupError("数据库名称为空，无法执行备份")

    backup_dir = _resolve_backup_dir(output_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target_path = backup_dir / f"{_safe_filename(db_name)}_{timestamp}.sql"
    tmp_path = target_path.with_name(f"{target_path.name}.tmp")

    command = _build_mysqldump_command(db_config, db_name)
    mysqldump_bin = command[0]
    if not shutil.which(mysqldump_bin):
        raise DatabaseBackupError(
            "未找到 mysqldump，请确认当前运行环境已安装 MySQL 客户端并加入 PATH"
        )

    env = os.environ.copy()
    password = str(db_config.get("PASSWORD") or "")
    if password:
        env["MYSQL_PWD"] = password

    try:
        with open(tmp_path, "wb") as output_file:
            completed = subprocess.run(
                list(command),
                stdout=output_file,
                stderr=subprocess.PIPE,
                env=env,
                check=False,
            )

        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace").strip()
            raise DatabaseBackupError(f"mysqldump 执行失败，退出码 {completed.returncode}: {stderr}")

        tmp_path.replace(target_path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise

    return MySQLBackupResult(
        path=target_path,
        database=db_name,
        size_bytes=target_path.stat().st_size,
        command=command,
    )


def _build_mysqldump_command(db_config: dict, db_name: str) -> tuple[str, ...]:
    command = [
        "mysqldump",
        "--single-transaction",
        "--quick",
        "--routines",
        "--triggers",
        "--events",
        "--default-character-set=utf8mb4",
        "--host",
        str(db_config.get("HOST") or "localhost"),
        "--port",
        str(db_config.get("PORT") or 3306),
    ]

    user = str(db_config.get("USER") or "").strip()
    if user:
        command.extend(["--user", user])

    command.append(db_name)
    return tuple(command)


def _resolve_backup_dir(output_dir: str | os.PathLike[str] | None) -> Path:
    backup_dir = Path(output_dir or BASE_DIR / "backups" / "sql").expanduser()
    if not backup_dir.is_absolute():
        backup_dir = BASE_DIR / backup_dir
    return backup_dir


def _safe_filename(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "database"
