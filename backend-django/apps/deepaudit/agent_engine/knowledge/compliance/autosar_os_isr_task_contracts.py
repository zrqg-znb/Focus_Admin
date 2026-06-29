"""AUTOSAR OS task and ISR contract guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


AUTOSAR_OS_ISR_TASK_CONTRACTS = KnowledgeDocument(
    id='autosar_os_isr_task_contracts',
    title='AUTOSAR OS Task/ISR 上下文约束',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['autosar', 'os', 'task', 'isr', 'interrupt', 'critical_section', 'schedule_table'],
    severity='medium',
    content="""
上下文检查
- ISR、Category 2 ISR、task、alarm、schedule table、callback 和 background loop 的可调用 API 集不同，必须先确定代码运行上下文。
- ISR/回调中出现阻塞调用、动态内存、日志、等待、长临界区或非 reentrant 服务时，需要检查平台契约和调度影响。
- 共享资源访问必须确认锁、SchM_Enter/Exit、SuspendAllInterrupts/ResumeAllInterrupts、GetResource/ReleaseResource 或 atomic 保护是否覆盖所有路径。
- 对死锁/竞态判断，要记录至少两个访问路径或锁顺序证据；只有单点 mutex 命中不得直接报告 confirmed。

证据闭环
- finding 需包含 task/ISR 名称、共享资源、读写点、保护机制、未保护路径或反例路径。
- 宏条件、配置开关和生成代码约束不明确时，结论降为 uncertain。
""".strip(),
)
