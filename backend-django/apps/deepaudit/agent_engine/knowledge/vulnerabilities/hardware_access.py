"""
硬件访问知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


HARDWARE_ACCESS = KnowledgeDocument(
    id="vuln_hardware_access",
    title="Hardware Access and Critical-Section Hazards",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["embedded", "mcu", "isr", "dma", "mmio", "register", "critical_section"],
    severity="high",
    cwe_ids=["CWE-362", "CWE-366", "CWE-667"],
    content="""
重点场景:
- ISR/IRQ 中直接访问寄存器、DMA 描述符或共享 MMIO 区域
- 任务上下文与中断上下文同时修改硬件状态
- 使用 volatile 但没有真正的同步、屏障或临界区保护
- 设备初始化、复位或使能顺序被打乱

审计清单:
1. 寄存器读写是否只发生在允许的上下文
2. DMA 描述符、缓冲区和状态位是否受保护
3. 是否需要内存屏障、cache flush/invalidate 或原子更新
4. 临界区是否足够短，且不会包含阻塞调用

修复思路:
- 将硬件访问集中到受控接口，限制上下文入口
- ISR 只做最小化工作并通过事件/队列下放
- 对共享寄存器、DMA 控制块和状态机使用显式同步
""",
)
