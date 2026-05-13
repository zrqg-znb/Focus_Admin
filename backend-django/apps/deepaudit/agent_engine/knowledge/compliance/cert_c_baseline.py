"""CERT C 基线检查"""

from ..base import KnowledgeCategory, KnowledgeDocument


CERT_C_BASELINE = KnowledgeDocument(
    id='cert_c_baseline',
    title='CERT C 基线检查',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['cert', 'cert_c', 'c', 'embedded', 'secure_coding', 'safety'],
    severity='low',
    content="""
检查重点
- 内存安全：越界、悬空引用、重复释放、未初始化读取
- 整数安全：溢出、截断、符号扩展和长度计算错误
- 并发与环境：竞争条件、锁顺序、上下文限制和异常返回处理

落地建议
- 把 CERT C 用作安全编码参考，而不是只在最终审查时补录
- 对驱动、协议解析、诊断报文和外设访问接口尤其要严格
- 若项目有安全目标，建议把 CERT C 规则映射到静态分析和代码评审项
""".strip(),
)
