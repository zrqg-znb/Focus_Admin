# DeepAudit 知识库维护 Wiki

本文档面向 DeepAudit 的日常使用者和维护者，回答四类问题：

- 知识库应该维护在哪里
- 如何新增、编辑、删除知识条目
- 如何让知识库和具体审计项目配合使用
- 团队协作时如何避免撞名、覆盖和知识失控

## 1. 知识库维护的基本原则

DeepAudit 的知识库建议分成两层维护：

### 1.1 共享基线知识

适合所有项目长期复用、需要跟代码一起评审和发布的知识，继续维护在内置模块里：

- `backend-django/apps/deepaudit/agent_engine/knowledge/vulnerabilities/`
- `backend-django/apps/deepaudit/agent_engine/knowledge/frameworks/`

这类知识通常是：

- 通用漏洞模式
- 框架级安全约束
- 长期稳定的审计规则

### 1.2 个人 / 团队 / 项目知识

日常新增的经验、误报边界、内部规范、项目坑点，默认维护成 `custom` 条目，不直接改内置代码模块。

推荐入口：

- 前端页面：`系统配置 -> 知识库`
- 后端接口：`/api/deepaudit/rag/knowledge/*`

运行时存储位置：

- `backend-django/media/deepaudit/knowledge/*.json`

这层知识更适合：

- 个人经验沉淀
- 团队专项检查清单
- 项目特有风险模式
- 误报排除规则
- 修复模板和上线门槛

## 2. 你应该怎么给知识条目命名

DeepAudit 现在把 `id` 当成真正的“模块名”使用，后续校验、检索和 Agent 注入都依赖这个值，所以 `id` 比标题更重要。

推荐固定命名：

- 个人知识：`custom_<name>_<topic>`
- 团队知识：`team_<domain>_<topic>`
- 项目知识：`proj_<project>_<topic>`

示例：

- `custom_zrq_jwt_review`
- `team_backend_auth_checklist`
- `proj_payment_idor_rules`

### 2.1 命名约束

- 必须显式填写 `id`
- 只能使用小写字母、数字、下划线和连字符
- 必须以字母或数字开头
- 不能使用内置保留前缀

当前保留前缀：

- `vuln_`
- `framework_`
- `vuln-`
- `framework-`

### 2.2 为什么必须显式写 `id`

因为系统会把同名 `id` 当成同一个自定义知识条目处理：

- 你保存相同 `id`，会覆盖你自己原来的条目
- 你不能覆盖内置知识的 `id`
- 你不能覆盖其他用户创建的自定义知识条目

所以多人协作时，先约定前缀和归属规则非常重要。

## 3. 每条知识应该包含哪些字段

建议每条知识至少维护以下字段：

- `id`
- `title`
- `content`
- `category`
- `tags`

按需补充：

- `severity`
- `cwe_ids`
- `owasp_ids`
- `metadata`

### 3.1 `category` 只用现有枚举

当前建议使用：

- `vulnerability`
- `framework`
- `best_practice`
- `remediation`
- `code_pattern`
- `compliance`

### 3.2 `tags` 必填

现在系统已经要求每条自定义知识至少有一个标签。原因很简单：

- 方便列表筛选
- 方便关键字搜索
- 方便语义检索召回
- 方便后续按项目、语言、框架聚类

推荐标签维度：

- 语言：`python`、`java`、`typescript`
- 框架：`django`、`spring`、`react`
- 风险点：`auth`、`idor`、`ssrf`
- 场景：`admin`、`payment`、`upload`
- 项目：`payment-core`、`crm-api`

## 4. 推荐的知识内容结构

为了让知识既能被人读，也能被检索和复用，建议统一成下面的结构：

```text
适用场景
- 

风险模式
- 

检测信号
- 

误报边界
- 

修复建议
- 

最小示例
- 
``` 

如果你不知道怎么开始写，至少先补齐这 6 部分：

- 适用于什么代码场景
- 风险通常长什么样
- 审计时看什么信号
- 什么情况不要误报
- 修复应该怎么做
- 给一段最小示例

## 5. 如何新增知识条目

DeepAudit 目前支持三种常用新增方式：

- 在前端知识库页手动创建
- 上传 `.json / .md / .markdown / .txt` 文件导入
- 通过 API 创建或导入

保存或上传成功后，系统会自动重建知识索引，通常不需要手动点“重建”。

### 5.1 方式一：在页面中手动新增

入口：

- `系统配置 -> 知识库`

操作步骤：

1. 打开知识库页，点击“新建知识条目”
2. 显式填写模块 `ID`
3. 填写标题、分类、标签
4. 按推荐结构填写内容
5. 点击保存

建议：

- 不要依赖标题自动推导 `id`
- 新条目优先使用 `custom_`、`team_`、`proj_` 前缀
- 标签不要留空
- 内容不要只写一句话，否则后续检索价值很低

### 5.2 方式二：上传文件导入

支持格式：

- `.json`
- `.md`
- `.markdown`
- `.txt`

操作步骤：

1. 打开 `系统配置 -> 知识库`
2. 点击“上传知识文件”
3. 选择文件
4. 显式填写 `document_id`
5. 补充标题、分类、标签等元信息
6. 提交上传

建议场景：

- 批量把审计 checklist 导入成知识条目
- 把团队历史 Markdown 手册迁移到 DeepAudit
- 把项目专项规范沉淀为可检索条目

### 5.3 通过 API 新增

创建或更新自定义知识条目：

```bash
curl -X POST "http://127.0.0.1:8001/api/deepaudit/rag/knowledge/modules" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "proj_payment_idor_rules",
    "title": "Payment 项目 IDOR 审计规则",
    "content": "适用场景\n- 支付单、退款单、交易详情接口\n\n风险模式\n- 仅校验对象存在，不校验归属关系",
    "category": "code_pattern",
    "tags": ["payment", "idor", "django"]
  }'
```

上传文件：

```bash
curl -X POST "http://127.0.0.1:8001/api/deepaudit/rag/knowledge/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@./payment-knowledge.md" \
  -F "document_id=proj_payment_gateway_notes" \
  -F "title=Payment 网关专项知识" \
  -F "category=best_practice" \
  -F "tags=payment" \
  -F "tags=gateway" \
  -F "tags=team"
```

## 6. 如何编辑知识条目

编辑知识条目的核心原则是：**同一个条目继续使用同一个 `id`**。

### 6.1 页面编辑

操作步骤：

1. 在知识库列表中找到目标条目
2. 打开详情或编辑弹窗
3. 修改标题、内容、标签等信息
4. 保存

编辑时建议优先维护这些内容：

- 补充误报边界
- 补充新的风险变体
- 把散乱内容整理成固定结构
- 补充修复建议和最小示例

### 6.2 编辑时要注意什么

- 如果你使用相同 `id` 保存，系统会覆盖你自己原来的自定义条目
- 如果该 `id` 属于内置知识，系统会拒绝覆盖
- 如果该 `id` 属于其他用户的自定义条目，系统会拒绝覆盖

这意味着编辑动作本质上就是“以同一个 `id` 重新保存”。

### 6.3 建议的编辑节奏

- 每次审计任务结束后，补充新发现的模式
- 每周整理一次零散条目，合并重复项
- 每月清理已经过时的规则和标签

## 7. 如何删除知识条目

DeepAudit 当前只允许删除 `custom` 来源的知识条目，内置知识默认只读。

### 7.1 页面删除

操作步骤：

1. 打开 `系统配置 -> 知识库`
2. 找到目标自定义条目
3. 点击删除
4. 确认删除

### 7.2 删除限制

只有同时满足下面条件才可以删：

- 条目来源是 `custom`
- 条目是你自己创建的，或者未记录 owner

删除后系统会自动重建知识索引。

### 7.3 API 删除

```bash
curl -X DELETE "http://127.0.0.1:8001/api/deepaudit/rag/knowledge/modules/proj_payment_idor_rules" \
  -H "Authorization: Bearer <token>"
```

## 8. 如何查找、校验和重建知识库

### 8.1 查列表

适合按分类、关键词、标签筛选：

- `GET /api/deepaudit/rag/knowledge/modules`

常用查询参数：

- `category`
- `keyword`
- `tag`

### 8.2 搜索知识

适合按关键字或语义召回：

- `POST /api/deepaudit/rag/knowledge/search`

如果没有配置 embedding，也可以使用普通关键字搜索；只是语义召回能力会弱一些。

### 8.3 校验模块名

如果你希望后续把某些知识条目显式传给 Agent 或其他工具链，先校验模块名是否有效：

- `POST /api/deepaudit/rag/knowledge/validate`

示例：

```bash
curl -X POST "http://127.0.0.1:8001/api/deepaudit/rag/knowledge/validate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "modules": ["proj_payment_idor_rules", "team_backend_auth_checklist"]
  }'
```

### 8.4 什么时候手动重建

以下情况建议手动执行一次重建：

- 批量导入了很多知识文件
- embedding 配置发生了变化
- 需要确认最新条目都已经进入向量索引

接口：

- `POST /api/deepaudit/rag/knowledge/rebuild`

## 9. 如何和项目一起使用

这一部分最关键。推荐你把“项目知识”当成审计项目的长期记忆层，而不是临时备忘录。

### 9.1 项目接入后的推荐动作

项目刚接入 DeepAudit 后，建议先补一批 `proj_` 条目：

- 这个项目常见的业务对象和权限边界
- 这个项目最容易误报的场景
- 这个项目使用的框架禁忌
- 这个项目的内部安全规范
- 这个项目已有的修复模板

例如：

- `proj_payment_auth_boundary`
- `proj_payment_idor_rules`
- `proj_payment_false_positive_cases`

这样做的好处是，知识会和项目上下文绑定，但又不会写死进通用规则。

### 9.2 推荐的项目协同流程

一个比较稳的流程是：

1. 项目接入后，先建立 3 到 5 条项目专项知识
2. 给这些条目打上统一标签，例如 `payment-core`、`django`、`auth`
3. 每次扫描或 Agent 审计后，把新的风险模式和误报边界补回这些条目
4. 每个版本迭代结束后，清理失效内容

### 9.3 和项目 RAG 的关系

DeepAudit 里其实有两类“知识”：

- 项目代码索引
- 安全知识库

两者不是一回事，但应该一起使用：

- 项目 RAG 解决“当前仓库代码里有什么”
- 安全知识库解决“我们应该重点关注什么、如何判断、如何修复”

一个简单理解是：

- 项目 RAG 面向代码事实
- 知识库面向审计经验

### 9.4 如何把知识模块交给 Agent 使用

当前后端和 Agent 工具链已经支持按模块名校验和注入知识模块，模块名就是知识条目的 `id`。

你可以这样理解：

- 条目先通过知识库维护成可复用模块
- 需要时先调用 `validate_knowledge_modules`
- 在支持 `knowledge_modules` 的 Agent / 工具链配置中显式传入这些模块名

适合显式注入的知识一般是：

- 项目专项规则
- 团队检查清单
- 某框架的固定坑点

如果当前某个页面还没有暴露“选择知识模块”的控件，也仍然建议先把知识条目按规范维护好，因为：

- 人可以直接查
- 搜索和校验接口已经能用
- 后续任务模板、Agent 工具链或二开接入时可以直接复用这些 `id`

### 9.5 最推荐的搭配方式

如果你问“最实用的一套做法是什么”，我建议是：

- 通用规则放内置知识
- 团队经验放 `team_` 条目
- 项目专项规则放 `proj_` 条目
- 审计前先确认项目专项条目已经存在
- 审计后立刻补充误报边界和修复建议

这样知识不会散在聊天记录或私人笔记里，而是会真正沉淀进系统。

## 10. 推荐的团队维护规则

如果是多人协作，建议先约定下面几件事：

### 10.1 前缀归属

- `custom_<name>_*` 归个人
- `team_<domain>_*` 归团队
- `proj_<project>_*` 归项目

### 10.2 标签规范

至少包含 2 到 3 类标签：

- 项目或系统标签
- 技术栈标签
- 风险类型标签

### 10.3 升级为内置知识的标准

只有满足下面条件，才建议把 `custom` 条目升级为内置代码模块：

- 不依赖某个个人经验
- 对大多数项目都有效
- 内容相对稳定
- 需要和代码版本一起评审、测试、发布

## 11. 常见问题

### 11.1 为什么我明明有标题，还是提示必须填写模块 ID

因为现在系统要求显式填写 `id`，不再推荐依赖标题自动生成。

### 11.2 为什么会提示标签不能为空

因为自定义知识已经要求至少一个标签，方便筛选、检索和模块复用。

### 11.3 为什么提示不能使用 `vuln_` 或 `framework_`

因为这些前缀保留给内置知识模块，避免和代码内置规则撞名。

### 11.4 为什么删不了

通常是这两种原因：

- 这个条目是内置知识，不允许删除
- 这个条目是其他用户创建的，你没有覆盖或删除权限

### 11.5 保存后为什么还搜不到

先确认下面几件事：

- 条目是否真的保存成功
- `id` 是否正确
- 是否使用了正确的关键词或标签
- embedding 是否已配置
- 如有批量导入或 embedding 变更，是否手动重建过索引

## 12. 一份推荐的日常工作流

如果你希望知识库真正帮助项目，而不是越积越乱，可以直接按下面执行：

1. 项目接入后，新建 3 到 5 条 `proj_` 条目
2. 每次审计结束后，把新模式和误报边界补进去
3. 每周整理一次标签和重复条目
4. 每月清理一轮过时内容
5. 对长期稳定、跨项目通用的知识，再升级进内置模块

这套流程的目标不是“把知识写多”，而是让知识能持续服务后续项目、扫描任务和 Agent 审计。

## 13. 附：一个推荐的项目知识条目示例

```json
{
  "id": "proj_payment_idor_rules",
  "title": "Payment 项目 IDOR 审计规则",
  "category": "code_pattern",
  "tags": ["payment-core", "idor", "django", "auth"],
  "severity": "high",
  "cwe_ids": ["CWE-639"],
  "owasp_ids": ["A01:2021"],
  "content": "适用场景\n- 支付单、退款单、交易明细查询接口\n\n风险模式\n- 通过 order_id、refund_id 直接读取对象，但未校验租户、用户或商户归属\n\n检测信号\n- queryset 仅按 id 查询\n- service 层没有 owner_id / tenant_id 约束\n- serializer 返回完整敏感对象\n\n误报边界\n- 后置策略层已经做了对象级权限校验\n- order_id 是服务端内部映射而非外部可控参数\n\n修复建议\n- 在对象查询阶段强制追加租户和归属条件\n- 对跨商户数据访问建立显式白名单\n\n最小示例\n- Order.objects.get(id=order_id, merchant_id=request.user.merchant_id)"
}
```

## 14. 相关入口速查

前端入口：

- `web/apps/web-deepaudit/src/components/system/KnowledgeBaseManager.tsx`
- `web/apps/web-deepaudit/src/components/system/SystemConfig.tsx`

后端接口：

- `backend-django/apps/deepaudit/rag/rag_api.py`

后端维护逻辑：

- `backend-django/apps/deepaudit/rag/rag_services.py`
- `backend-django/apps/deepaudit/agent_engine/knowledge/rag_knowledge.py`

内置知识目录：

- `backend-django/apps/deepaudit/agent_engine/knowledge/vulnerabilities/`
- `backend-django/apps/deepaudit/agent_engine/knowledge/frameworks/`

运行时自定义知识目录：

- `backend-django/media/deepaudit/knowledge/`
