"""DMA 缓冲生命周期与缓存一致性"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_DMA_BUFFER_LIFECYCLE = KnowledgeDocument(
    id='c_dma_buffer_lifecycle',
    title='DMA 缓冲生命周期与缓存一致性',
    category=KnowledgeCategory.CODE_PATTERN,
    tags=['c', 'embedded', 'automotive', 'dma', 'cache', 'buffer', 'coherency', 'descriptor'],
    severity='high',
    content="""
识别信号
- DMA descriptor、buffer、transfer complete、cache flush / invalidate
- 发送缓冲区和接收缓冲区在中断与任务之间共享

关注点
- 缓冲区在 DMA 完成前是否被提前释放或重新复用
- descriptor / status / owner bit 是否有清晰的所有权模型
- 非一致性缓存平台上是否遗漏了 flush / invalidate / barrier
- 是否存在对齐不满足、长度不一致或双缓冲切换错误

建议
- 将 DMA 生命周期拆成 prepare / submit / complete / release 四段
- 在完成中断中只投递事件，不要做大块数据搬运
- 对 tx / rx 缓冲建立单独的状态机和回收路径
- 尽量用静态或池化内存管理 DMA 相关对象
""".strip(),
)
