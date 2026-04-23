import sys
import time
import textwrap
import paramiko


HOST = "8.146.236.192"
USER = "root"
PASSWORD = "Zrqznb020528!"


def connect_with_retry(retries: int = 12, sleep_s: int = 6) -> paramiko.SSHClient:
    last_error = None
    for i in range(retries):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                HOST,
                22,
                USER,
                PASSWORD,
                timeout=20,
                banner_timeout=60,
                auth_timeout=60,
            )
            print(f"[OK] SSH connected on attempt {i + 1}")
            return ssh
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"[WARN] connect attempt {i + 1} failed: {exc}")
            time.sleep(sleep_s)
    raise RuntimeError(f"SSH connection failed after retries: {last_error}")


def run(ssh: paramiko.SSHClient, cmd: str, timeout: int = 3600) -> str:
    print("\n----- RUN -----")
    print(cmd)
    chan = ssh.get_transport().open_session()
    chan.get_pty()
    chan.exec_command(cmd)
    chunks: list[str] = []
    start = time.time()
    while True:
        if chan.recv_ready():
            chunks.append(chan.recv(8192).decode("utf-8", "ignore"))
        if chan.recv_stderr_ready():
            chunks.append(chan.recv_stderr(8192).decode("utf-8", "ignore"))
        if chan.exit_status_ready() and (not chan.recv_ready()) and (not chan.recv_stderr_ready()):
            break
        if time.time() - start > timeout:
            chan.close()
            raise TimeoutError(f"Command timeout: {cmd}")
        time.sleep(0.2)
    code = chan.recv_exit_status()
    output = "".join(chunks)
    print(f"----- EXIT {code} -----")
    print(output[-8000:])
    if code != 0:
        raise RuntimeError(f"Command failed({code}): {cmd}")
    return output


def upload_text(ssh: paramiko.SSHClient, path: str, content: str) -> None:
    sftp = ssh.open_sftp()
    try:
        with sftp.file(path, "w") as f:
            f.write(content)
    finally:
        sftp.close()
    print(f"[OK] Uploaded: {path}")


def main() -> int:
    ssh = connect_with_retry()
    try:
        # 1) Build and publish frontend.
        run(ssh, "cd /srv/focus/Focus_Admin/web && pnpm install --frozen-lockfile", timeout=3600)
        run(ssh, "cd /srv/focus/Focus_Admin/web && pnpm build:ele", timeout=3600)
        run(ssh, "cd /srv/focus/Focus_Admin/web && pnpm build:deepaudit", timeout=3600)
        run(
            ssh,
            (
                "mkdir -p /var/www/focus /var/www/deepaudit "
                "&& rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-ele/dist/ /var/www/focus/ "
                "&& rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-deepaudit/dist/ /var/www/deepaudit/"
            ),
            timeout=600,
        )

        nginx_conf = textwrap.dedent(
            """\
            map $http_upgrade $connection_upgrade {
                default upgrade;
                ''      close;
            }

            upstream focus_backend {
                server 127.0.0.1:8001;
                keepalive 32;
            }

            server {
                listen 80;
                server_name zrqznb.work 8.146.236.192;

                client_max_body_size 500M;
                root /var/www/focus;
                index index.html;

                location / {
                    try_files $uri $uri/ /index.html;
                }

                location = /deepaudit-app {
                    return 301 /deepaudit-app/;
                }

                location /deepaudit-app/ {
                    alias /var/www/deepaudit/;
                    index index.html;
                    try_files $uri $uri/ /deepaudit-app/index.html;
                }

                location /static/ {
                    alias /srv/focus/Focus_Admin/backend-django/static_root/;
                    access_log off;
                    expires 7d;
                    add_header Cache-Control "public";
                }

                location /media/ {
                    alias /srv/focus/Focus_Admin/backend-django/media/;
                }

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
        upload_text(ssh, "/etc/nginx/conf.d/focus.conf", nginx_conf)

        service_backend = textwrap.dedent(
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
            ExecStart=/srv/focus/venv/bin/gunicorn application.asgi:application -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8001 --workers 4 --timeout 120
            Restart=always
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
            """
        )
        service_default = textwrap.dedent(
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
            ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q celery -n focus-default@%%h -l info --concurrency=2 --max-tasks-per-child=5
            Restart=always
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
            """
        )
        service_deepaudit = textwrap.dedent(
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
            ExecStart=/srv/focus/venv/bin/python -m celery -A application worker -Q deepaudit -n focus-deepaudit@%%h -l info --concurrency=2 --prefetch-multiplier=1 --max-tasks-per-child=5
            Restart=always
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
            """
        )
        service_scheduler = textwrap.dedent(
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
        upload_text(ssh, "/etc/systemd/system/focus-backend.service", service_backend)
        upload_text(ssh, "/etc/systemd/system/focus-celery-default.service", service_default)
        upload_text(ssh, "/etc/systemd/system/focus-celery-deepaudit.service", service_deepaudit)
        upload_text(ssh, "/etc/systemd/system/focus-scheduler.service", service_scheduler)

        run(ssh, "nginx -t && systemctl reload nginx", timeout=120)
        run(
            ssh,
            "systemctl daemon-reload && systemctl enable --now focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler",
            timeout=180,
        )
        run(ssh, "systemctl is-active focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler", timeout=120)
        run(ssh, "lsof -iTCP:8001 -sTCP:LISTEN -P -n", timeout=120)
        run(ssh, "curl -I --max-time 15 http://127.0.0.1/ && curl -I --max-time 15 http://127.0.0.1/deepaudit-app/", timeout=120)
        run(
            ssh,
            "curl -I --max-time 15 http://zrqznb.work/ && curl -I --max-time 15 http://zrqznb.work/deepaudit-app/ && curl -I --max-time 15 http://zrqznb.work/basic-api/",
            timeout=180,
        )
        run(
            ssh,
            "systemctl --no-pager --full status focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler | tail -n 120",
            timeout=120,
        )
    finally:
        ssh.close()

    print("\\n[ALL DONE]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
