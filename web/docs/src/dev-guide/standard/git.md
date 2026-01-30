# Git 规范

## 分支管理

| 分支 | 说明 |
| --- | --- |
| `main` | 主分支，稳定版本 |
| `develop` | 开发分支 |
| `feature/*` | 功能分支 |
| `bugfix/*` | 修复分支 |
| `release/*` | 发布分支 |

## 工作流程

1. 从 `develop` 创建功能分支
2. 开发完成后提交 PR
3. Code Review 通过后合并
4. 定期将 `develop` 合并到 `main`

```bash
# 创建功能分支
git checkout develop
git pull origin develop
git checkout -b feature/user-management

# 开发完成后提交
git add .
git commit -m "feat: 添加用户管理功能"
git push origin feature/user-management
```

## Commit 规范

使用 Conventional Commits 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type 类型

| Type | 说明 |
| --- | --- |
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式 |
| `refactor` | 重构 |
| `test` | 测试 |
| `chore` | 构建/工具 |

### 示例

```bash
# 新功能
git commit -m "feat(user): 添加用户导出功能"

# Bug 修复
git commit -m "fix(auth): 修复登录失败问题"

# 文档更新
git commit -m "docs: 更新 API 文档"
```

## 提交检查

项目已配置 commitlint 和 lefthook：

```bash
# 安装 git hooks
lefthook install
```

错误的 commit 格式将被拒绝。
