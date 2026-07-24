# Agent Tools / Skill Optimizer

Skill Optimizer 是 `apps.agent_tools.skill_optimizer` 下的专用 Agent，用于分析、评测并迭代改写上传技能包中的 `SKILL.md`。它通过 OpenAI Chat Completions 兼容接口调用用户配置的模型，不运行上传包内的脚本。

接口前缀为 `/api/agent-tools/skill-optimizer`。模型档案属于当前用户；API Key 仅以模块自有 Fernet 加密字段保存，不在任何接口响应中下发。优化任务进入独立的 `skill_optimizer` Celery 队列，任务、评分与下载结果均会持久化。
