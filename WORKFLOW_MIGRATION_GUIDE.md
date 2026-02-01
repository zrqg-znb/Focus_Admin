# Focus_workflow 工作流功能迁移到 Focus_Admin 指南

## 一、项目差异概览

### 1.1 后端模块差异

| 模块 | Focus_workflow | Focus_Admin | 移植必要性 |
|------|----------------|-------------|------------|
| `workflow/` | ✅ | ❌ | **必须** |
| `message/` | ✅ | ❌ | **必须** |
| `form_manager/` | ✅ | ❌ | 建议（表单关联）|
| `form_data_manager/` | ✅ | ❌ | 建议（表单数据）|
| `page_manager/` | ✅ | ❌ | 可选 |
| `contract/` | ✅ | ❌ | 可选 |
| `data_source/` | ✅ | ❌ | 可选 |
| `code_generator/` | ✅ | ❌ | 可选 |

### 1.2 前端差异

| 类型 | Focus_workflow 独有 |
|------|---------------------|
| API | `workflow.ts`, `message.ts`, `announcement.ts`, `form-manager.ts`, `form-data.ts` |
| 组件 | `workflow/`, `notification/`, `import-export-manager/`, `multi-data-view/` |
| Store | 消息通知相关 store |

---

## 二、移植步骤

### 步骤 1：更新 Python 依赖

编辑 `Focus_Admin/backend-django/requirements.txt`，添加以下依赖：

```txt
# WebSocket 支持 (channels-redis)
channels-redis~=4.3.0

# MinIO 对象存储（如需要）
minio==7.2.20

# HTTP 客户端
httpx==0.28.1
```

执行安装：
```bash
cd Focus_Admin/backend-django
pip install -r requirements.txt
```

---

### 步骤 2：移植后端核心模块

#### 2.1 移植 Message 模块（消息通知）

```bash
# 复制整个 message 目录
cp -r Focus_workflow/backend-django/core/message Focus_Admin/backend-django/core/
```

**包含文件：**
- `message_model.py` - 消息数据模型
- `message_service.py` - 消息服务（含 WebSocket 推送）
- `message_api.py` - 消息 API
- `message_schema.py` - 数据验证 Schema
- `announcement_model.py` - 公告模型
- `announcement_service.py` - 公告服务
- `announcement_api.py` - 公告 API
- `announcement_schema.py` - 公告 Schema

#### 2.2 移植 Workflow 模块

```bash
# 复制整个 workflow 目录
cp -r Focus_workflow/backend-django/core/workflow Focus_Admin/backend-django/core/
```

**包含文件：**
- `workflow_model.py` - 工作流数据模型（定义、实例、任务、日志）
- `workflow_api.py` - 工作流 API 接口
- `workflow_service.py` - 工作流核心服务
- `workflow_schema.py` - 数据验证 Schema
- `progress_service.py` - 流程进度服务
- `engine/` - 工作流引擎
  - `workflow_engine.py` - 工作流引擎主文件
  - `assignee_resolver.py` - 审批人解析器
  - `condition_evaluator.py` - 条件评估器
  - `delay_process.py` - 延时处理
  - `task_timeout_process.py` - 任务超时处理
  - `handlers/` - 节点处理器

#### 2.3 移植 Form 相关模块（建议）

工作流通常需要关联表单，建议同时移植：

```bash
# 复制表单管理模块
cp -r Focus_workflow/backend-django/core/form_manager Focus_Admin/backend-django/core/

# 复制表单数据模块
cp -r Focus_workflow/backend-django/core/form_data_manager Focus_Admin/backend-django/core/
```

---

### 步骤 3：更新后端路由配置

编辑 `Focus_Admin/backend-django/core/router.py`，添加以下内容：

```python
# === 新增导入 ===
from core.workflow.workflow_api import router as workflow_router
from core.message.message_api import router as message_router
from core.message.announcement_api import router as announcement_router
# 如果移植了表单模块
from core.form_manager.form_api import router as form_manager_router
from core.form_data_manager.form_data_api import router as form_data_router

# === 新增路由注册（添加到现有路由注册之后）===
core_router.add_router("/workflow", workflow_router, tags=["Core-Workflow"])
core_router.add_router("/message", message_router, tags=["Core-Message"])
core_router.add_router("/announcement", announcement_router, tags=["Core-Announcement"])
# 如果移植了表单模块
core_router.add_router("/form", form_manager_router, tags=["Core-FormManager"])
core_router.add_router("/form-data", form_data_router, tags=["Core-FormData"])
```

---

### 步骤 4：更新 Settings 配置

编辑 `Focus_Admin/backend-django/application/settings.py`，在文件末尾添加：

```python
# ================================================= #
# ********************* 企业微信配置 ******************* #
# ================================================= #
WECOM_CORP_ID = ""  # 企业ID
WECOM_AGENT_ID = ""  # 应用AgentId
WECOM_SECRET = ""  # 应用Secret

# ================================================= #
# ********************* 钉钉配置 ******************* #
# ================================================= #
DINGTALK_APP_KEY = ""  # 应用AppKey
DINGTALK_APP_SECRET = ""  # 应用AppSecret
DINGTALK_AGENT_ID = ""  # 应用AgentId

# ================================================= #
# ********************* 飞书配置 ******************* #
# ================================================= #
FEISHU_APP_ID = ""  # 应用App ID
FEISHU_APP_SECRET = ""  # 应用App Secret

# ================================================= #
# ********************* 前端地址配置 ******************* #
# ================================================= #
FRONTEND_URL = "http://localhost:5555"  # 前端地址，用于消息跳转链接

# 通知短信模板（如需短信通知）
ALIYUN_SMS_NOTIFY_TEMPLATE_CODE = ""  # 通知短信模板代码
```

---

### 步骤 5：执行数据库迁移

```bash
cd Focus_Admin/backend-django

# 生成迁移文件
python manage.py makemigrations

# 执行迁移
python manage.py migrate
```

**新增数据表：**
- `workflow_definition` - 工作流定义
- `workflow_instance` - 工作流实例
- `workflow_task` - 工作流任务
- `workflow_log` - 工作流日志
- `core_message` - 站内消息
- `core_announcement` - 公告（如有）

---

### 步骤 6：移植前端 API 接口

```bash
# 复制工作流 API
cp Focus_workflow/web/apps/web-ele/src/api/core/workflow.ts \
   Focus_Admin/web/apps/web-ele/src/api/core/

# 复制消息 API
cp Focus_workflow/web/apps/web-ele/src/api/core/message.ts \
   Focus_Admin/web/apps/web-ele/src/api/core/

# 复制公告 API
cp Focus_workflow/web/apps/web-ele/src/api/core/announcement.ts \
   Focus_Admin/web/apps/web-ele/src/api/core/

# 如果移植了表单模块
cp Focus_workflow/web/apps/web-ele/src/api/core/form-manager.ts \
   Focus_Admin/web/apps/web-ele/src/api/core/
cp Focus_workflow/web/apps/web-ele/src/api/core/form-data.ts \
   Focus_Admin/web/apps/web-ele/src/api/core/
```

---

### 步骤 7：移植前端组件

#### 7.1 工作流组件

```bash
# 复制工作流组件目录
cp -r Focus_workflow/web/apps/web-ele/src/components/workflow \
      Focus_Admin/web/apps/web-ele/src/components/
```

**包含：**
- `designer/` - 工作流设计器
- `detial/` - 工作流详情展示
- `index.ts` - 组件导出

#### 7.2 通知组件

```bash
# 复制通知组件目录
cp -r Focus_workflow/web/apps/web-ele/src/components/notification \
      Focus_Admin/web/apps/web-ele/src/components/
```

**包含：**
- `NotificationDrawer.vue` - 通知抽屉组件
- `NotificationPopup.vue` - 通知弹窗组件

#### 7.3 其他相关组件（可选）

```bash
# 导入导出管理器
cp -r Focus_workflow/web/apps/web-ele/src/components/import-export-manager \
      Focus_Admin/web/apps/web-ele/src/components/

# 多数据视图
cp -r Focus_workflow/web/apps/web-ele/src/components/multi-data-view \
      Focus_Admin/web/apps/web-ele/src/components/
```

---

### 步骤 8：移植前端页面（视图）

根据需要复制工作流相关页面：

```bash
# 查看 Focus_workflow 的视图结构，找到工作流相关页面
ls -la Focus_workflow/web/apps/web-ele/src/views/

# 复制需要的页面到 Focus_Admin（根据实际目录结构调整）
```

---

### 步骤 9：更新前端路由

在 Focus_Admin 的前端路由配置中添加工作流相关路由。

编辑路由配置文件（通常在 `src/router/` 目录下），添加：

```typescript
// 工作流管理路由
{
  path: '/workflow',
  name: 'Workflow',
  meta: { title: '工作流管理' },
  children: [
    {
      path: 'definition',
      name: 'WorkflowDefinition',
      component: () => import('@/views/workflow/definition/index.vue'),
      meta: { title: '流程定义' }
    },
    {
      path: 'instance',
      name: 'WorkflowInstance',
      component: () => import('@/views/workflow/instance/index.vue'),
      meta: { title: '流程实例' }
    },
    {
      path: 'task',
      name: 'WorkflowTask',
      component: () => import('@/views/workflow/task/index.vue'),
      meta: { title: '待办任务' }
    }
  ]
}

// 消息中心路由
{
  path: '/message',
  name: 'Message',
  component: () => import('@/views/message/index.vue'),
  meta: { title: '消息中心' }
}
```

---

### 步骤 10：安装前端依赖并验证

```bash
cd Focus_Admin/web

# 安装依赖
pnpm install

# 启动开发服务器验证
pnpm dev
```

---

## 三、验证清单

### 3.1 后端验证

- [ ] 依赖安装成功 (`pip install -r requirements.txt`)
- [ ] 数据库迁移成功 (`python manage.py migrate`)
- [ ] 启动服务无报错 (`python manage.py runserver`)
- [ ] API 接口可访问：
  - [ ] `/api/core/workflow/` - 工作流接口
  - [ ] `/api/core/message/` - 消息接口
  - [ ] `/api/core/announcement/` - 公告接口
- [ ] WebSocket 通知推送正常

### 3.2 前端验证

- [ ] 前端编译无错误
- [ ] 工作流设计器可正常加载
- [ ] 工作流发起流程正常
- [ ] 工作流审批流程正常
- [ ] 消息通知接收正常
- [ ] 通知组件显示正常

---

## 四、注意事项

1. **数据库兼容性**：确保两个项目使用相同的数据库类型（MySQL/PostgreSQL）

2. **用户模型**：工作流依赖 `core.User` 模型，确保以下字段存在：
   - `wechat_unionid` - 企业微信用户ID（可选）
   - `dingtalk_unionid` - 钉钉用户ID（可选）
   - `feishu_union_id` - 飞书用户ID（可选）
   - `mobile` - 手机号（短信通知需要）
   - `email` - 邮箱（邮件通知需要）

3. **WebSocket 配置**：确保 `channels-redis` 配置正确，Redis 服务正常运行

4. **定时任务**：如需超时处理等功能，确保 Celery 或 APScheduler 正常运行

5. **前端依赖**：检查工作流组件是否需要额外的 npm 包

6. **菜单配置**：移植完成后需要在系统菜单中添加工作流相关菜单项

---

## 五、常见问题

### Q1: 迁移时提示模型不存在
确保先移植 `message` 模块，再移植 `workflow` 模块，因为工作流依赖消息模块。

### Q2: WebSocket 连接失败
检查 `settings.py` 中的 `CHANNEL_LAYERS` 配置，确保 Redis 连接信息正确。

### Q3: 前端组件报错
检查是否缺少依赖组件，可能需要同时移植 `zq-form`、`zq-table` 等基础组件。

### Q4: 审批人解析失败
检查 `assignee_resolver.py` 中引用的部门、角色等模型是否与 Focus_Admin 兼容。

---

## 六、文件清单汇总

### 后端文件
```
core/
├── message/                    # 消息模块
│   ├── __init__.py
│   ├── message_model.py
│   ├── message_service.py
│   ├── message_api.py
│   ├── message_schema.py
│   ├── announcement_model.py
│   ├── announcement_service.py
│   ├── announcement_api.py
│   └── announcement_schema.py
├── workflow/                   # 工作流模块
│   ├── __init__.py
│   ├── workflow_model.py
│   ├── workflow_api.py
│   ├── workflow_service.py
│   ├── workflow_schema.py
│   ├── progress_service.py
│   └── engine/
│       ├── __init__.py
│       ├── workflow_engine.py
│       ├── assignee_resolver.py
│       ├── condition_evaluator.py
│       ├── delay_process.py
│       ├── task_timeout_process.py
│       ├── base.py
│       ├── utils.py
│       └── handlers/
├── form_manager/               # 表单管理（可选）
└── form_data_manager/          # 表单数据（可选）
```

### 前端文件
```
src/
├── api/core/
│   ├── workflow.ts
│   ├── message.ts
│   ├── announcement.ts
│   ├── form-manager.ts         # 可选
│   └── form-data.ts            # 可选
├── components/
│   ├── workflow/
│   │   ├── designer/
│   │   ├── detial/
│   │   └── index.ts
│   └── notification/
│       ├── NotificationDrawer.vue
│       └── NotificationPopup.vue
└── views/
    ├── workflow/               # 工作流页面
    └── message/                # 消息中心
```
