"""AUTOSAR Classic Platform context guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


AUTOSAR_CLASSIC_PLATFORM = KnowledgeDocument(
    id='autosar_classic_platform',
    title='AUTOSAR Classic Platform 分层上下文',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['autosar', 'classic_platform', 'rte', 'bsw', 'asw', 'mcal', 'automotive'],
    severity='medium',
    content="""
分层判断
- ASW/RTE/BSW/MCAL/Complex Driver 层级不同，接口契约和可调用上下文不同；审计前先识别模块所在层。
- RTE API、BSW service API 和 MCAL register access 不应混为普通函数调用；必须确认调用者任务、初始化状态和配置生成关系。
- 生成代码、供应商栈、配置头文件和手写 glue code 要分开评价，避免把受配置约束的代码当作普通业务输入。

证据要求
- 记录模块边界、入口 API、被调用服务、关联配置/宏和上下游调用路径。
- 对接口违约类问题，必须说明违反的上下文：初始化顺序、reentrancy、同步/异步模式、返回值/错误码处理或状态机约束。
""".strip(),
)
