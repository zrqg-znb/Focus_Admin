"""环形缓冲区与生产者/消费者协议"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_RING_BUFFER = KnowledgeDocument(
    id='c_ring_buffer',
    title='环形缓冲区与生产者/消费者协议',
    category=KnowledgeCategory.CODE_PATTERN,
    tags=['c', 'embedded', 'automotive', 'ring_buffer', 'queue', 'buffer', 'isr', 'task'],
    severity='medium',
    content="""
识别信号
- head / tail / read / write / wrap / modulo / mask 这类索引更新逻辑
- ISR 生产者、任务消费者、双缓冲或队列式数据流

关注点
- 头尾指针是否存在竞态更新、丢写、覆盖未读数据或空满混淆
- 单生产者单消费者模型是否被多上下文悄悄打破
- 计数器和索引是否在溢出、回绕或整型截断后仍然正确
- 对齐、缓存一致性和内存可见性是否被忽略

建议
- 明确定义 full / empty 判定规则，不要依赖隐式约定
- 对跨上下文更新使用原子操作、轻量锁或临界区
- 把读写封装成小函数，避免在业务逻辑里直接操作索引
- 对 DMA / ISR 场景补充 cache flush / invalidate 与顺序约束
""".strip(),
)
