# Tools / Agent Skills

Agent Skills 是 `apps.tools` 下的独立 AI 工具。它通过 OpenAI Chat Completions 兼容接口分析、评测并迭代改写 `SKILL.md`，不运行上传包中的任何脚本。

接口前缀为 `/api/tools/agent-skills`。模型档案由 `tools_admin` 或超级管理员维护；API Key 只以模块自有 Fernet 加密字段保存，不在接口响应中下发。优化任务进入 `agent_skills` Celery 队列，所有任务、评分和下载结果都会持久化。
