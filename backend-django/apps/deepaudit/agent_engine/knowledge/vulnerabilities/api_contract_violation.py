"""
API 契约误用知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


API_CONTRACT_VIOLATION = KnowledgeDocument(
    id="vuln_api_contract_violation",
    title="API Contract Violation",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["api", "contract", "return_value", "error_handling", "embedded"],
    severity="medium",
    cwe_ids=["CWE-252", "CWE-670"],
    content="""
典型信号:
- 忽略返回值、错误码和状态位
- 未满足前置条件就调用驱动/HAL/API
- 错误的所有权假设导致二次释放或悬空引用
- 设备初始化顺序、线程上下文或中断上下文约束被破坏

审计清单:
1. API 文档要求的前置条件是否满足
2. 返回值与错误码是否被检查并传播
3. 调用方和被调方对缓冲区、生命周期、线程上下文的约定是否一致

修复思路:
- 明确接口契约并在边界处校验
- 对所有关键 API 返回值做处理
- 用类型/封装表达所有权与上下文约束
""",
)
