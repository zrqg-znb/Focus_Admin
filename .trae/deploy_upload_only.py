import os
import stat
import time
import textwrap
from pathlib import Path

import paramiko


HOST = "8.146.236.192"
USER = "root"
PASSWORD = "Zrqznb020528!"

LOCAL_ELE_DIST = Path("/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-ele/dist")
LOCAL_DEEPAUDIT_DIST = Path("/Users/zrq/CodeSpace/PythonProjects/Focus_Admin/web/apps/web-deepaudit/dist")
REMOTE_ELE = "/var/www/focus"
REMOTE_DEEPAUDIT = "/var/www/deepaudit"


def connect() -> paramiko.SSHClient:
    last = None
    for i in range(12):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(HOST, 22, USER, PASSWORD, timeout=20, banner_timeout=60, auth_timeout=60)
            print(f"[OK] SSH connected attempt {i + 1}")
            return ssh
        except Exception as e:  # noqa: BLE001
            last = e
            print(f"[WARN] connect {i + 1} failed: {e}")
            time.sleep(5)
    raise RuntimeError(f"SSH connect failed: {last}")


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> str:
    chan = ssh.get_transport().open_session()
    chan.get_pty()
    chan.exec_command(cmd)
    out = []
    start = time.time()
    while True:
        if chan.recv_ready():
            out.append(chan.recv(8192).decode("utf-8", "ignore"))
        if chan.recv_stderr_ready():
            out.append(chan.recv_stderr(8192).decode("utf-8", "ignore"))
        if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
            break
        if time.time() - start > timeout:
            chan.close()
            raise TimeoutError(cmd)
        time.sleep(0.2)
    code = chan.recv_exit_status()
    text = "".join(out)
    print(f"\n[CMD] {cmd}\n[EXIT] {code}\n{text[-2000:]}")
    if code != 0:
        raise RuntimeError(cmd)
    return text


def _mkdirs(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    path = ""
    for p in parts:
        path += "/" + p
        try:
            sftp.stat(path)
        except OSError:
            sftp.mkdir(path)


def _rmtree(sftp: paramiko.SFTPClient, remote_path: str) -> None:
    try:
        attrs = sftp.listdir_attr(remote_path)
    except OSError:
        return
    for attr in attrs:
        p = f"{remote_path}/{attr.filename}"
        if stat.S_ISDIR(attr.st_mode):
            _rmtree(sftp, p)
            try:
                sftp.rmdir(p)
            except OSError:
                pass
        else:
            try:
                sftp.remove(p)
            except OSError:
                pass


def upload_dir(sftp: paramiko.SFTPClient, local_dir: Path, remote_dir: str) -> None:
    _mkdirs(sftp, remote_dir)
    _rmtree(sftp, remote_dir)
    for root, dirs, files in os.walk(local_dir):
        rel = os.path.relpath(root, str(local_dir))
        target = remote_dir if rel == "." else f"{remote_dir}/{rel}"
        _mkdirs(sftp, target)
        for d in dirs:
            _mkdirs(sftp, f"{target}/{d}")
        for f in files:
            lp = os.path.join(root, f)
            rp = f"{target}/{f}"
            sftp.put(lp, rp)
    print(f"[OK] uploaded {local_dir} -> {remote_dir}")


def main() -> int:
    if not LOCAL_ELE_DIST.exists() or not LOCAL_DEEPAUDIT_DIST.exists():
        raise RuntimeError("local dist missing, please build first")

    ssh = connect()
    try:
        run(ssh, "mkdir -p /var/www/focus /var/www/deepaudit /srv/focus/Focus_Admin/backend-django/static_root /srv/focus/Focus_Admin/backend-django/media")
        sftp = ssh.open_sftp()
        upload_dir(sftp, LOCAL_ELE_DIST, REMOTE_ELE)
        upload_dir(sftp, LOCAL_DEEPAUDIT_DIST, REMOTE_DEEPAUDIT)
        sftp.close()

        nginx_conf = textwrap.dedent(
            """\
            map $http_upgrade $connection_upgrade {
                default upgrade;
                ''      close;
            }
            upstream focus_backend { server 127.0.0.1:8001; keepalive 32; }
            server {
                listen 80;
                server_name zrqznb.work 8.146.236.192;
                client_max_body_size 500M;
                root /var/www/focus;
                index index.html;
                location / { try_files $uri $uri/ /index.html; }
                location = /deepaudit-app { return 301 /deepaudit-app/; }
                location /deepaudit-app/ { alias /var/www/deepaudit/; index index.html; try_files $uri $uri/ /deepaudit-app/index.html; }
                location /static/ { alias /srv/focus/Focus_Admin/backend-django/static_root/; access_log off; expires 7d; add_header Cache-Control "public"; }
                location /media/ { alias /srv/focus/Focus_Admin/backend-django/media/; }
                location ~ ^/basic-api/api/deepaudit/agent-tasks/[^/]+/stream$ {
                    rewrite ^/basic-api/(.*)$ /$1 break;
                    proxy_pass http://focus_backend;
                    proxy_http_version 1.1;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    proxy_buffering off;
                    proxy_cache off;
                    proxy_set_header X-Accel-Buffering no;
                    chunked_transfer_encoding on;
                    proxy_read_timeout 3600s;
                    proxy_send_timeout 3600s;
                    proxy_connect_timeout 30s;
                }
                location /basic-api/ {
                    proxy_pass http://focus_backend/;
                    proxy_http_version 1.1;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    proxy_read_timeout 300s;
                    proxy_send_timeout 300s;
                }
                location /ws/ {
                    proxy_pass http://focus_backend;
                    proxy_http_version 1.1;
                    proxy_set_header Upgrade $http_upgrade;
                    proxy_set_header Connection $connection_upgrade;
                    proxy_set_header Host $host;
                    proxy_set_header X-Real-IP $remote_addr;
                    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                    proxy_set_header X-Forwarded-Proto $scheme;
                    proxy_read_timeout 3600s;
                    proxy_send_timeout 3600s;
                }
            }
            """
        )
        sftp = ssh.open_sftp()
        with sftp.file("/etc/nginx/conf.d/focus.conf", "w") as f:
            f.write(nginx_conf)
        sftp.close()

        run(ssh, "nginx -t && systemctl reload nginx")
        # services may or may not already exist; start if exists
        run(ssh, "systemctl daemon-reload")
        run(ssh, "systemctl restart focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler || true")
        run(ssh, "systemctl is-active nginx redis-server || true")
        run(ssh, "curl -I --max-time 20 http://127.0.0.1/ || true")
        run(ssh, "curl -I --max-time 20 http://127.0.0.1/deepaudit-app/ || true")
        run(ssh, "curl -I --max-time 20 http://127.0.0.1/basic-api/ || true")
    finally:
        ssh.close()

    print("[ALL DONE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
