# Docker 部署

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+

## 目录结构

```
deploy/
├── docker-compose.yml
├── nginx/
│   └── nginx.conf
├── backend/
│   └── Dockerfile
└── .env
```

## docker-compose.yml

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend
    restart: always

  backend:
    build:
      context: ../backend-django
      dockerfile: ../deploy/backend/Dockerfile
    volumes:
      - ../backend-django:/app
    environment:
      - DJANGO_ENV=production
    depends_on:
      - mysql
      - redis
    restart: always

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_PASSWORD}
      MYSQL_DATABASE: focus_admin
    volumes:
      - mysql_data:/var/lib/mysql
    restart: always

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data
    restart: always

volumes:
  mysql_data:
  redis_data:
```

## 后端 Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 收集静态文件
RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "application.wsgi:application", "-b", "0.0.0.0:8000", "-w", "4"]
```

## 部署步骤

### 1. 构建前端

```bash
cd web
pnpm build:ele
cp -r apps/web-ele/dist ../deploy/frontend/
```

### 2. 配置环境变量

```bash
cd deploy
cp .env.example .env
# 编辑 .env 文件
```

### 3. 启动服务

```bash
docker-compose up -d
```

### 4. 初始化数据库

```bash
docker-compose exec backend python manage.py migrate
docker-compose exec backend python manage.py createsuperuser
```

## 常用命令

```bash
# 查看日志
docker-compose logs -f backend

# 重启服务
docker-compose restart backend

# 停止服务
docker-compose down

# 重新构建
docker-compose up -d --build
```
