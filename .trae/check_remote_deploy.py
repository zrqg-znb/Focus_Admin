import time
import paramiko


HOST = "8.146.236.192"
USER = "root"
PWD = "Zrqznb020528!"


def main() -> int:
    ssh = None
    last_error = None
    for i in range(8):
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                HOST,
                22,
                USER,
                PWD,
                timeout=20,
                banner_timeout=60,
                auth_timeout=60,
            )
            print(f"SSH connected on attempt {i + 1}")
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            print(f"connect attempt {i + 1} failed: {exc}")
            time.sleep(5)

    if ssh is None:
        raise RuntimeError(f"SSH connect failed: {last_error}")

    cmd = """
set -e
hostname
date
echo "=== services ==="
systemctl is-active nginx || true
systemctl is-active redis-server || true
systemctl is-active focus-backend || true
systemctl is-active focus-celery-default || true
systemctl is-active focus-celery-deepaudit || true
systemctl is-active focus-scheduler || true
echo "=== port ==="
lsof -iTCP:8001 -sTCP:LISTEN -P -n || true
echo "=== localhost ==="
curl -I --max-time 15 http://127.0.0.1/ || true
curl -I --max-time 15 http://127.0.0.1/deepaudit-app/ || true
curl -I --max-time 15 http://127.0.0.1/basic-api/ || true
echo "=== domain ==="
curl -I --max-time 15 http://zrqznb.work/ || true
curl -I --max-time 15 http://zrqznb.work/deepaudit-app/ || true
curl -I --max-time 15 http://zrqznb.work/basic-api/ || true
echo "=== systemd status tail ==="
systemctl --no-pager --full status focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler | tail -n 120 || true
"""

    stdin, stdout, stderr = ssh.exec_command(cmd, get_pty=True, timeout=600)
    out = stdout.read().decode("utf-8", "ignore")
    err = stderr.read().decode("utf-8", "ignore")
    print(out)
    if err.strip():
        print("STDERR:")
        print(err)

    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
