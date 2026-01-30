# 后端环境搭建

## 环境要求

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

## 安装步骤

### 1. 克隆代码

```bash
git clone https://github.com/jiangzhikj/zq-platform.git
cd Focus_Admin/backend-django
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置数据库

创建 MySQL 数据库：

```sql
CREATE DATABASE focus_admin DEFAULT CHARACTER SET utf8mb4;
```

修改 `env/dev_env.py` 中的数据库配置：

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'focus_admin',
        'USER': 'root',
        'PASSWORD': 'your_password',
        'HOST': '127.0.0.1',
        'PORT': '3306',
    }
}
```

### 5. 配置 Redis

修改 `env/dev_env.py` 中的 Redis 配置：

```python
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_PASSWORD = ''
REDIS_DB = 0
```

### 6. 执行数据库迁移

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. 创建管理员账号

```bash
python manage.py createsuperuser
```

### 8. 启动开发服务器

```bash
python manage.py runserver 0.0.0.0:8000
```

## 启动任务调度器

如需使用定时任务功能：

```bash
python start_scheduler.py
```

## 验证安装

访问 `http://localhost:8000/api/docs` 查看 API 文档。

## 常见问题

### MySQL 连接错误

确保 MySQL 服务已启动，并检查用户名密码是否正确。

### Redis 连接错误

确保 Redis 服务已启动：

```bash
redis-server
```

### 依赖安装失败

尝试使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```
