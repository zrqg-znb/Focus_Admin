"""
嵌入式并发知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


EMBEDDED_CONCURRENCY = KnowledgeDocument(
    id="vuln_embedded_concurrency",
    title="Embedded Concurrency Hazards",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["embedded", "mcu", "isr", "rtos", "race_condition", "shared_memory"],
    severity="high",
    cwe_ids=["CWE-362", "CWE-366"],
    content="""
重点场景:
- ISR 与任务共享缓冲区、寄存器镜像、环形队列
- volatile 代替同步原语
- 临界区太大或跨越耗时操作
- 多核/多上下文共享 DMA、驱动状态或静态缓存

审计清单:
1. 共享变量是否真正具备原子性
2. ISR 是否只做最小工作并把重任务下放
3. 环形缓冲区 head/tail 更新是否受保护
4. 是否存在丢中断、竞态覆盖或顺序可见性问题

修复思路:
- 对共享状态使用原子操作或正确的锁
- ISR 只设置标志位或投递事件
- 明确内存屏障、缓存一致性和驱动状态机
""",
)
