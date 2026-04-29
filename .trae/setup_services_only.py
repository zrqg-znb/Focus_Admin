import textwrap
import paramiko


HOST = "8.146.236.192"
USER = "root"
PASSWORD = "Zrqznb020528!"


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 300) -> None:
    _, so, se = ssh.exec_command(cmd, get_pty=True, timeout=timeout)
    out = so.read().decode("utf-8", "ignore")
    err = se.read().decode("utf-8", "ignore")
    print(f"\n[CMD] {cmd}\n{out}")
    if err.strip():
        print("STDERR:")
        print(err)


def main() -> int:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, 22, USER, PASSWORD, timeout=20, banner_timeout=60, auth_timeout=60)

    backend_service = textwrap.dedent(
        """\
        [Unit]
        Description=Focus Django ASGI Backend
        After=network.target redis-server.service
        Requires=redis-server.service

        [Service]
        Type=simple
        User=root
        Group=root
        WorkingDirectory=/srv/focus/Focus_Admin/backend-django
        EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
        Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
        Environment=ENABLE_SCHEDULER=false
        ExecStart=/srv/focus/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 2 --timeout 120
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    )
    celery_default = textwrap.dedent(
        """\
        [Unit]
        Description=Focus Celery Worker (default)
        After=network.target redis-server.service focus-backend.service
        Requires=redis-server.service

        [Service]
        Type=simple
        User=root
        Group=root
        WorkingDirectory=/srv/focus/Focus_Admin/backend-django
        EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
        Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
        Environment=ENABLE_SCHEDULER=false
        ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q celery -n focus-default@%%h -l info --concurrency=1 --max-tasks-per-child=5
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    )
    celery_deepaudit = textwrap.dedent(
        """\
        [Unit]
        Description=Focus Celery Worker (deepaudit)
        After=network.target redis-server.service focus-backend.service
        Requires=redis-server.service

        [Service]
        Type=simple
        User=root
        Group=root
        WorkingDirectory=/srv/focus/Focus_Admin/backend-django
        EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
        Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
        Environment=ENABLE_SCHEDULER=false
        ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q deepaudit -n focus-deepaudit@%%h -l info --concurrency=1 --prefetch-multiplier=1 --max-tasks-per-child=5
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    )
    scheduler_service = textwrap.dedent(
        """\
        [Unit]
        Description=Focus Scheduler
        After=network.target redis-server.service focus-backend.service
        Requires=redis-server.service

        [Service]
        Type=simple
        User=root
        Group=root
        WorkingDirectory=/srv/focus/Focus_Admin/backend-django
        EnvironmentFile=/srv/focus/Focus_Admin/backend-django/.env
        Environment=PATH=/srv/focus/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin
        Environment=ENABLE_SCHEDULER=false
        ExecStart=/srv/focus/venv/bin/python start_scheduler.py
        Restart=always
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    )

    sftp = ssh.open_sftp()
    with sftp.file("/etc/systemd/system/focus-backend.service", "w") as f:
        f.write(backend_service)
    with sftp.file("/etc/systemd/system/focus-celery-default.service", "w") as f:
        f.write(celery_default)
    with sftp.file("/etc/systemd/system/focus-celery-deepaudit.service", "w") as f:
        f.write(celery_deepaudit)
    with sftp.file("/etc/systemd/system/focus-scheduler.service", "w") as f:
        f.write(scheduler_service)
    sftp.close()

    run(ssh, "cd /srv/focus/Focus_Admin/backend-django && /srv/focus/venv/bin/python manage.py collectstatic --noinput")
    run(ssh, "cd /srv/focus/Focus_Admin/backend-django && /srv/focus/venv/bin/python manage.py init_deepaudit")
    run(ssh, "systemctl daemon-reload")
    run(ssh, "systemctl enable --now focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler")
    run(ssh, "systemctl is-active focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler")
    run(ssh, "lsof -iTCP:8001 -sTCP:LISTEN -P -n")
    run(ssh, "curl -I --max-time 20 -H 'Host: zrqznb.work' http://127.0.0.1/")
    run(ssh, "curl -I --max-time 20 -H 'Host: zrqznb.work' http://127.0.0.1/deepaudit-app/")
    run(ssh, "curl -I --max-time 20 -H 'Host: zrqznb.work' http://127.0.0.1/basic-api/")

    ssh.close()
    print("\n[SETUP DONE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
