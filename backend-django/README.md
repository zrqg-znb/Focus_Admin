## 运行教程
### 克隆项目
```bash
git clone https://gitee.com/fuadmin/fu-admin.git
# 进入项目目录
cd fu-admin/backend
```

### 在 `config/env.py` 中配置数据库信息
```bash
# 默认是Postgres SQL
# 数据库类型 MYSQL/SQLSERVER/SQLITE3/POSTGRESQL
DATABASE_TYPE = "MYSQL"
# 数据库地址
DATABASE_HOST = "127.0.0.1"
# 数据库端口
DATABASE_PORT = 3306
# 数据库用户名
DATABASE_USER = "fuadmin"
# 数据库密码
DATABASE_PASSWORD = "fuadmin"
# 数据库名
DATABASE_NAME = "fu-admin-pro"
```

### 安装依赖环境
```bash
pip install -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple -r requirements.txt
```

### 执行迁移命令
```bash
python manage.py makemigrations system
```
```bash
python manage.py migrate
```
### 初始化数据
```bash
python manage.py loaddata db_init.json
```
### 启动项目
```bash
python manage.py runserver 0.0.0.0:8000
```

### Scheduler(MySQL) 长时间运行连接断开
如果以独立进程或常驻线程运行 scheduler（例如 `start_scheduler.py` / APScheduler），MySQL 连接在空闲一段时间后可能被服务端断开，从而在任务执行时出现 `MySQL server has gone away`。

项目侧建议：
- MySQL 数据库配置启用 `CONN_HEALTH_CHECKS` 并设置合适的 `CONN_MAX_AGE`（已在 `application/settings.py` 的 MySQL 配置中加入）。
- 在非请求上下文（线程池任务、事件监听器、监控循环）执行 ORM 前后调用 `close_old_connections()`，避免复用陈旧连接（scheduler 模块已做统一处理）。

```bash
python manage.py dumpdata system --indent 4 > db_init.json
```
