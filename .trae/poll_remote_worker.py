import time
import paramiko


HOST = "8.146.236.192"
USER = "root"
PASSWORD = "Zrqznb020528!"


def main() -> int:
    for round_num in range(1, 11):
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
            cmd = """
set -e
STATUS=$(cat /tmp/focus_deploy_worker.status 2>/dev/null || echo MISSING)
echo STATUS:$STATUS
if [ -f /tmp/focus_deploy_worker.log ]; then tail -n 80 /tmp/focus_deploy_worker.log; fi
if [ "$STATUS" = "SUCCESS" ]; then
  echo '--- VERIFY ---'
  systemctl is-active focus-backend focus-celery-default focus-celery-deepaudit focus-scheduler || true
  lsof -iTCP:8001 -sTCP:LISTEN -P -n || true
  curl -I --max-time 15 http://127.0.0.1/ || true
  curl -I --max-time 15 http://127.0.0.1/deepaudit-app/ || true
  curl -I --max-time 15 http://127.0.0.1/basic-api/ || true
fi
"""
            _, so, se = ssh.exec_command(cmd, get_pty=True, timeout=180)
            out = so.read().decode("utf-8", "ignore")
            err = se.read().decode("utf-8", "ignore")
            ssh.close()
            print(f"\n===== ROUND {round_num} =====")
            print(out[-12000:])
            if err.strip():
                print("STDERR:")
                print(err)
            if "STATUS:SUCCESS" in out or "STATUS:FAILED" in out:
                break
        except Exception as exc:  # noqa: BLE001
            print(f"ROUND {round_num} connect error: {exc}")
        time.sleep(30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
