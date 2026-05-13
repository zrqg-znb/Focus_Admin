"""C 接口契约与边界校验"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_API_CONTRACT_BOUNDARY = KnowledgeDocument(
    id='c_api_contract_boundary',
    title='C 接口契约与边界校验',
    category=KnowledgeCategory.CODE_PATTERN,
    tags=['c', 'embedded', 'automotive', 'api', 'contract', 'boundary', 'return_value', 'error_handling'],
    severity='medium',
    content="""
识别信号
- 函数依赖注释、命名约定或外部文档来隐式表达前置条件
- 返回值、错误码、参数长度和上下文约束没有被明确校验

关注点
- 调用方和被调用方对所有权、长度、上下文和可重入性的理解是否一致
- 输出参数是否在失败路径上保持定义良好，不会留下半初始化数据
- 运行上下文是否匹配：ISR、任务、初始化阶段、关机阶段
- 边界条件是否被显式处理，而不是靠默认值掩盖

建议
- 在 API 入口处集中校验参数、长度和上下文
- 返回值要被检查并向上层传播，不要静默吞掉错误
- 对重要接口使用清晰的状态码和文档化约定
- 若接口涉及 ownership transfer，应在命名或类型上体现
""".strip(),
)
