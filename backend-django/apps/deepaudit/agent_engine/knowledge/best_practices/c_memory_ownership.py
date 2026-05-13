"""C 语言内存所有权与生命周期"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_MEMORY_OWNERSHIP = KnowledgeDocument(
    id='c_memory_ownership',
    title='C 语言内存所有权与生命周期',
    category=KnowledgeCategory.BEST_PRACTICE,
    tags=['c', 'embedded', 'automotive', 'memory', 'ownership', 'lifecycle', 'malloc', 'free'],
    severity='medium',
    content="""
适用场景
- 动态内存、静态缓存、对象池、句柄封装、跨模块缓存返回值
- 汽车底层软件中常见的缓冲区、消息对象、诊断数据和驱动上下文

核心原则
- 一个对象只应有一个明确所有者，释放责任要能追溯到唯一出口
- 借用指针和拥有指针要区分，函数签名中要表达长度、所有权和有效期
- 释放之后立即失效化，避免继续传递或二次释放
- 不要返回栈上地址，也不要把局部缓冲区的生命周期伪装成长期对象

审计要点
- 检查 malloc/new/open/lock 之后是否在每条错误路径上都能回收
- 检查结构体成员、全局缓存、回调参数是否存在隐式共享所有权
- 检查 driver/HAL 接口是否清楚声明调用方和被调用方各自负责什么
- 检查 ISR / 任务 / DMA 三个上下文是否共用同一块内存而没有生命周期协议

建议
- 用显式的 owner 字段、长度字段或句柄封装对象生命周期
- 在 cleanup 分支中按逆序释放资源，并确保 cleanup 可重入
- 对外暴露的 API 尽量返回状态码和输出参数，而不是裸指针
""".strip(),
)
