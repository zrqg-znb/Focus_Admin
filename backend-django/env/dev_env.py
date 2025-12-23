# ************** 默认数据库 配置  ************** #
# ================================================= #
# 数据库类型 MYSQL/SQLSERVER/SQLITE3/POSTGRESQL
import os

# 允许通用环境变量覆盖（.env 中的 DATABASE_*）
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', "MYSQL")
# 数据库地址（优先 DEV_DB_HOST，其次 DATABASE_HOST，最后默认值）
DATABASE_HOST = os.environ.get('DEV_DB_HOST', os.environ.get('DATABASE_HOST', "rm-2ze7td37h05fd80qnpo.mysql.rds.aliyuncs.com"))
# 数据库端口
DATABASE_PORT = int(os.environ.get('DEV_DB_PORT', os.environ.get('DATABASE_PORT', 3306)))
# 数据库用户名
DATABASE_USER = os.environ.get('DEV_DB_USER', os.environ.get('DATABASE_USER', ""))
# 数据库密码
DATABASE_PASSWORD = os.environ.get('DEV_DB_PASSWORD', os.environ.get('DATABASE_PASSWORD', ""))
# 数据库名
DATABASE_NAME = os.environ.get('DEV_DB_NAME', os.environ.get('DATABASE_NAME', "focus_admin"))

# ================================================= #
# ******** redis配置  *********** #
# ================================================= #
REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD', '')
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
REDIS_DB = os.environ.get('REDIS_DB', '2')
REDIS_URL = f'redis://:{REDIS_PASSWORD or ""}@{REDIS_HOST}:6379'



# # ================================================= #
# # ******************** JWT 配置 ***************** #
# # ================================================= #

# JWT 密钥从环境变量读取
JWT_ACCESS_SECRET_KEY = os.environ.get(
    'JWT_ACCESS_SECRET_KEY',
    'default-access-secret-key-change-in-production'
)
JWT_REFRESH_SECRET_KEY = os.environ.get(
    'JWT_REFRESH_SECRET_KEY',
    'default-refresh-secret-key-change-in-production'
)



# ================================================= #
# ******** 其他配置 *********** #
# ================================================= #
IS_DEMO = False

ENABLE_SCHEDULER = True

# ================================================= #
# ******** OAuth 配置 *********** #
# ================================================= #

# 是否给OAuth登陆用户授予管理员权限（生产环境最好不要这样做）
GRANT_ADMIN_TO_OAUTH_USER = False

# Gitee OAuth
GITEE_CLIENT_ID = os.environ.get('GITEE_CLIENT_ID', '292df743a2f82df6000cc6f5c5271d8a67c2f4fdd03fd9c0b0b34f2727845397')
GITEE_CLIENT_SECRET = os.environ.get('GITEE_CLIENT_SECRET', '697f5fa9459d837aecdb163756e8ea340e916cc4f3a56ca89f8925df9199d2e9')
# 注意：前端端口是 5777，回调路径是 /oauth/gitee/callback
GITEE_REDIRECT_URI = os.environ.get('GITEE_REDIRECT_URI', 'http://localhost:5777/oauth/gitee/callback')
