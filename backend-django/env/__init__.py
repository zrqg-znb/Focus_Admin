import os
from pathlib import Path

# 简易 .env 加载（无第三方依赖）
def _load_dotenv():
    try:
        env_file = Path(__file__).resolve().parent.parent / '.env'
        if env_file.exists():
            for raw_line in env_file.read_text(encoding='utf-8').splitlines():
                line = raw_line.strip()
                if not line or line.startswith('#'):
                    continue
                # 去除行内注释
                if '#' in line:
                    line = line.split('#', 1)[0].strip()
                if '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and (key not in os.environ):
                    os.environ[key] = value
    except Exception:
        # 加载失败不影响后续流程
        pass

_load_dotenv()

# dev, uat, prd
ENV = os.environ.get('ZQ_ENV', 'dev')

if ENV == 'dev':
    from env.dev_env import *
elif ENV == 'uat':
    from env.uat_env import *
elif ENV == 'prd':
    from env.prd_env import *


