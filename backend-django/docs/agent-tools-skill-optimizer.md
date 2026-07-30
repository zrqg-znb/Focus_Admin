# Agent Tools / Skill Optimizer

Skill Optimizer 是 `apps.agent_tools.skill_optimizer` 下的专用 Agent，用于分析、评测并迭代改写上传技能包中的 `SKILL.md`。它通过 AI 辅助工具平台的 OpenAI Chat Completions 兼容模型连接调用用户配置的模型，不运行上传包内的脚本。

Skill Optimizer 接口前缀为 `/api/agent-tools/skill-optimizer`；平台级模型连接接口为 `/api/agent-tools/providers`，由 `apps.agent_tools.providers` 统一维护，供后续所有 Agent 复用。模型档案属于当前用户；API Key 仅以平台自有 Fernet 加密字段保存，不在任何接口响应中下发。优化任务进入独立的 `skill_optimizer` Celery 队列，任务、评分与下载结果均会持久化。

## 内网模型恢复策略

平台级 `providers` 服务会对 `408`、`425`、`429`、`500`、`502`、`503`、`504` 以及连接/读取超时执行带抖动的指数退避重试，并优先遵守上游返回的 `Retry-After`。每次模型调用的总恢复窗口默认是 300 秒；超过窗口后任务会以“模型服务在 300 秒内未恢复”失败。`400`、`401`、`403`、`404` 等配置、鉴权或请求错误会直接失败，不会等待。

Skill Optimizer 的调用轨迹会在等待期间显示“正在等待模型服务恢复”，因此任务仍在运行而不是卡死。以下环境变量可按部署容量调整，修改后需重启 Web 与 Celery Worker：

```dotenv
AGENT_TOOLS_MODEL_RECOVERY_TIMEOUT_SECONDS=300
AGENT_TOOLS_MODEL_CONNECT_TIMEOUT_SECONDS=10
AGENT_TOOLS_MODEL_READ_TIMEOUT_SECONDS=120
AGENT_TOOLS_MODEL_RETRY_INITIAL_DELAY_SECONDS=2
AGENT_TOOLS_MODEL_RETRY_MAX_DELAY_SECONDS=30
```
