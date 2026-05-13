"""AUTOSAR 风格检查"""

from ..base import KnowledgeCategory, KnowledgeDocument


AUTOSAR_C_BASELINE = KnowledgeDocument(
    id='autosar_c_baseline',
    title='AUTOSAR 风格检查',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['autosar', 'autosar_c', 'c', 'automotive', 'embedded', 'interface', 'deterministic'],
    severity='low',
    content="""
检查重点
- 接口是否明确、可预测、可组合，是否避免隐藏状态和隐式副作用
- 初始化、生命周期、错误处理和上下文约束是否清晰可追踪
- 是否避免在实时或安全关键路径上引入不确定行为

落地建议
- 对汽车项目优先检查模块边界、接口命名、数据所有权和时序依赖
- ISR、任务、驱动和基础软件层之间要有明确分层和同步策略
- 动态内存、日志和阻塞调用应当在关键路径上受限或被审查
""".strip(),
)
