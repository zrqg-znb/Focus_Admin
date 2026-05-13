"""资源回收与单出口展开"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_RESOURCE_CLEANUP_UNWIND = KnowledgeDocument(
    id='c_resource_cleanup_unwind',
    title='资源回收与单出口展开',
    category=KnowledgeCategory.REMEDIATION,
    tags=['c', 'embedded', 'automotive', 'cleanup', 'resource', 'goto', 'free', 'lock'],
    severity='medium',
    content="""
典型问题
- 多个 early return 导致部分资源未释放
- 锁、文件句柄、DMA 资源、内存对象、IRQ 状态释放顺序不一致

修复建议
- 用统一的 cleanup 标签或退出块完成逆序回收
- 清理逻辑要幂等，避免重复释放或者二次解锁
- 成功路径和失败路径都要覆盖资源回收
- 资源释放后尽快把句柄置空或标记为无效

落地方式
- 在驱动、协议栈、诊断流程里把 acquire / release 成对设计
- 对复杂函数增加资源表或状态图，减少漏回收路径
- 对于汽车底层软件，优先保证异常路径不会把系统留在半初始化状态
""".strip(),
)
