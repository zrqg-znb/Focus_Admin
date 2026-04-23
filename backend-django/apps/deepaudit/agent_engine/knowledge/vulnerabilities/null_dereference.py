"""
空指针解引用知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


NULL_DEREFERENCE = KnowledgeDocument(
    id="vuln_null_dereference",
    title="Null Dereference",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "null", "pointer", "lifetime"],
    severity="high",
    cwe_ids=["CWE-476"],
    content="""
典型信号:
- 资源申请、查表、回调返回值未检查直接解引用
- 复杂条件分支后假设指针一定非空
- ISR/任务切换导致共享对象在访问前被置空

审计清单:
1. 每个解引用点前是否存在可靠非空约束
2. 错误码和返回值是否被忽略
3. 初始化顺序是否允许对象在使用前为空

修复思路:
- 统一前置条件检查
- 让工厂/初始化函数显式返回错误
- 对共享资源访问增加状态检查和同步
""",
)
