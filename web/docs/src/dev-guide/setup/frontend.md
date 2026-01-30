# 前端环境搭建

## 环境要求

- Node.js 18+
- pnpm 8+

## 安装步骤

### 1. 安装 Node.js

推荐使用 nvm 管理 Node.js 版本：

```bash
# 安装 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# 安装 Node.js 18
nvm install 18
nvm use 18
```

### 2. 安装 pnpm

```bash
npm install -g pnpm
```

### 3. 克隆代码

```bash
git clone https://github.com/jiangzhikj/zq-platform.git
cd Focus_Admin/web
```

### 4. 安装依赖

```bash
pnpm install
```

::: tip 提示
如果安装速度较慢，可以设置国内镜像：

```bash
pnpm config set registry https://registry.npmmirror.com
```
:::

### 5. 配置环境变量

修改 `apps/web-ele/.env.development`：

```env
# API 地址
VITE_GLOB_API_URL=/api

# 代理配置
VITE_PROXY=[["/api","http://localhost:8000"]]
```

### 6. 启动开发服务器

```bash
# 启动 Element Plus 版本
pnpm dev:ele
```

访问 `http://localhost:5173`

## 其他命令

```bash
# 构建生产版本
pnpm build:ele

# 代码检查
pnpm lint

# 修复代码格式
pnpm lint:fix

# 预览构建结果
pnpm preview
```

## IDE 配置

### VS Code 推荐插件

- Vue - Official (Volar)
- ESLint
- Prettier
- Tailwind CSS IntelliSense
- TypeScript Vue Plugin

### 配置文件

项目已包含 VS Code 配置文件：

- `.vscode/settings.json` - 编辑器设置
- `.vscode/extensions.json` - 推荐插件

## 常见问题

### 依赖安装失败

清除缓存后重新安装：

```bash
pnpm store prune
rm -rf node_modules
pnpm install
```

### 端口被占用

修改 `apps/web-ele/vite.config.mts` 中的端口配置：

```typescript
export default defineConfig({
  server: {
    port: 5174 // 修改端口
  }
})
```
