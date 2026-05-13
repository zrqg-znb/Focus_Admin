"""RTOS / ISR 边界与并发约束"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_INTERRUPT_BOUNDARY = KnowledgeDocument(
    id='c_interrupt_boundary',
    title='RTOS / ISR 边界与并发约束',
    category=KnowledgeCategory.BEST_PRACTICE,
    tags=['c', 'embedded', 'automotive', 'rtos', 'isr', 'irq', 'critical_section', 'task'],
    severity='medium',
    content="""
适用场景
- 中断服务例程、定时器回调、任务调度、信号量/事件通知、共享状态更新
- FreeRTOS / 裸机 / RTOS 混合工程中的任务与中断协作

核心原则
- ISR 只做最小化工作：采样、置位、投递事件、唤醒任务
- 阻塞、等待、长循环、复杂解析和动态分配尽量不要出现在中断上下文
- 临界区要足够短，且只包住真正需要原子保护的共享状态
- 跨上下文共享数据要用明确同步原语，而不是依赖 volatile 代替同步

审计要点
- 检查 ISR 是否调用了可能阻塞的 API、日志系统或分配器
- 检查任务和 ISR 是否同时读写同一缓冲区、状态机或寄存器镜像
- 检查队列、信号量、事件组、原子变量是否真的覆盖了并发窗口
- 检查 memory barrier、cache flush/invalidate、重排序约束是否被遗漏

建议
- 把耗时逻辑下放到任务或工作队列
- 对共享状态使用显式锁、原子操作或单向消息传递
- 只在必要边界内使用 taskENTER_CRITICAL / taskEXIT_CRITICAL 之类的保护
""".strip(),
)
