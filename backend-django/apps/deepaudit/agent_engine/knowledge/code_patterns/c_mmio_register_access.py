"""MMIO / 寄存器访问模式"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_MMIO_REGISTER_ACCESS = KnowledgeDocument(
    id='c_mmio_register_access',
    title='MMIO / 寄存器访问模式',
    category=KnowledgeCategory.CODE_PATTERN,
    tags=['c', 'embedded', 'automotive', 'mmio', 'register', 'volatile', 'readl', 'writel', 'hardware'],
    severity='high',
    content="""
识别信号
- readl / writel / ioread / iowrite / 直接寄存器地址解引用
- volatile 读写、位操作、读改写、状态轮询、硬件标志位清除

关注点
- volatile 只能约束编译器优化，不能替代同步、锁和内存屏障
- 多个上下文同时更新同一寄存器或 shadow state 时容易出现丢写
- 读改写流程是否需要原子保护，是否会被中断打断
- 寄存器写入顺序、posted write、cache 和 barrier 约束是否明确

建议
- 封装统一的寄存器访问接口，明确上下文和访问顺序
- 在需要时显式使用屏障、临界区或互斥机制
- 不要把硬件状态直接暴露给业务层反复修改
- 对清状态位、使能位和 DMA 控制寄存器分别建模
""".strip(),
)
