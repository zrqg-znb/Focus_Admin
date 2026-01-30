# 快速开始

本文将指导你如何快速搭建 Focus Admin 的开发环境。

## 环境准备

### 后端环境

- Python 3.10+
- MySQL 8.0+
- Redis 6.0+

### 前端环境

- Node.js 18+
- pnpm 8+

## 获取代码

```bash
# 克隆仓库
git clone https://github.com/jiangzhikj/zq-platform.git

# 进入项目目录
cd Focus_Admin
```

## 后端启动

### 1. 创建虚拟环境

```bash
cd backend-django

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

修改 `env/dev_env.py` 中的数据库配置：

```python
# 数据库配置
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

# Redis 配置
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
```

### 4. 初始化数据库

```bash
# 创建数据库迁移
python manage.py makemigrations

# 执行迁移
python manage.py migrate

# 创建超级用户（可选）
python manage.py createsuperuser
```

### 5. 启动后端服务

```bash
python manage.py runserver 0.0.0.0:8000
```

后端 API 文档访问地址：`http://localhost:8000/api/docs`

## 前端启动

### 1. 安装依赖

```bash
cd web

# 安装 pnpm（如果没有安装）
npm install -g pnpm

# 安装项目依赖
pnpm install
```

### 2. 配置 API 地址

修改 `apps/web-ele/.env.development`：

```env
VITE_GLOB_API_URL=/api
```

### 3. 启动开发服务器

```bash
# 启动 Element Plus 版本
pnpm dev:ele
```

前端访问地址：`http://localhost:5173`

## 默认账号

| 账号 | 密码 | 说明 |
| --- | --- | --- |
| admin | admin123 | 超级管理员 |

## 开发建议

### IDE 推荐

- **后端**: PyCharm / VS Code + Python 插件
- **前端**: VS Code + Volar 插件

### VS Code 推荐插件

```json
{
  "recommendations": [
    "vue.volar",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ms-python.python"
  ]
}
```

## 常见问题

### 后端问题

**Q: 数据库连接失败？**

检查数据库服务是否启动，以及配置文件中的连接信息是否正确。

**Q: Redis 连接失败？**

确保 Redis 服务已启动，默认端口为 6379。

### 前端问题

**Q: pnpm install 很慢？**

设置国内镜像源：

```bash
pnpm config set registry https://registry.npmmirror.com
```

**Q: Node.js 版本不对？**

推荐使用 nvm 管理 Node.js 版本：

```bash
nvm install 18
nvm use 18
```

## 下一步

- [技术栈说明](/overview/tech-stack)
- [系统架构](/overview/architecture)
- [后端模块概览](/backend/core/overview)
- [前端目录结构](/frontend/project-structure)
