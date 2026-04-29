import time
import textwrap
import paramiko


HOST = "8.146.236.192"
USER = "root"
PASSWORD = "Zrqznb020528!"


REMOTE_SCRIPT = textwrap.dedent(
    """\
    #!/usr/bin/env bash
    set -euo pipefail
    LOG=/tmp/focus_deploy_worker.log
    STATUS=/tmp/focus_deploy_worker.status
    echo RUNNING > "$STATUS"
    {
      cd /srv/focus/Focus_Admin/backend-django
      /srv/focus/venv/bin/python manage.py collectstatic --noinput
      /srv/focus/venv/bin/python manage.py init_deepaudit

      cd /srv/focus/Focus_Admin/web
      pnpm install --frozen-lockfile
      pnpm build:ele
      pnpm build:deepaudit

      mkdir -p /var/www/focus /var/www/deepaudit
      rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-ele/dist/ /var/www/focus/
      rsync -av --delete /srv/focus/Focus_Admin/web/apps/web-deepaudit/dist/ /var/www/deepaudit/

      cat >/etc/nginx/conf.d/focus.conf <<'EOF'
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
            rewrite ^/basic-api/(.*)$ /$1 break; proxy_pass http://focus_backend; proxy_http_version 1.1;
            proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;
            proxy_buffering off; proxy_cache off; proxy_set_header X-Accel-Buffering no; chunked_transfer_encoding on;
            proxy_read_timeout 3600s; proxy_send_timeout 3600s; proxy_connect_timeout 30s;
        }
        location /basic-api/ {
            proxy_pass http://focus_backend/; proxy_http_version 1.1;
            proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 300s; proxy_send_timeout 300s;
        }
        location /ws/ {
            proxy_pass http://focus_backend; proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;
            proxy_read_timeout 3600s; proxy_send_timeout 3600s;
        }
    }
    EOF
      nginx -t
      systemctl reload nginx

      cat >/etc/systemd/system/focus-backend.service <<'EOF'
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
    EOF

      cat >/etc/systemd/system/focus-celery-default.service <<'EOF'
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
    EOF

      cat >/etc/systemd/system/focus-celery-deepaudit.service <<'EOF'
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
    EOF

      cat >/etc/systemd/system/focus-scheduler.service <<'EOF'
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
    EOF

      systemctl daemon-reload
      systemctl enable --now focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler
      echo SUCCESS > "$STATUS"
    } > "$LOG" 2>&1 || { echo FAILED > "$STATUS"; exit 1; }
    """
)


def main() -> int:
    last_error = None
    for i in range(20):
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
            sftp = ssh.open_sftp()
            with sftp.file("/tmp/focus_deploy_worker.sh", "w") as f:
                f.write(REMOTE_SCRIPT)
            sftp.chmod("/tmp/focus_deploy_worker.sh", 0o755)
            sftp.close()
            _, so, se = ssh.exec_command(
                "nohup bash /tmp/focus_deploy_worker.sh >/tmp/focus_deploy_worker.nohup 2>&1 & echo STARTED",
                get_pty=True,
                timeout=60,
            )
            print(so.read().decode("utf-8", "ignore"))
            err = se.read().decode("utf-8", "ignore")
            if err.strip():
                print(err)
            ssh.close()
            print("LAUNCHED")
            return 0
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"retry {i + 1} failed: {exc}")
            time.sleep(5)
    raise RuntimeError(f"launch failed: {last_error}")


if __name__ == "__main__":
    raise SystemExit(main())
