"""AUTOSAR C++14 production audit guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


AUTOSAR_CPP14_RULES = KnowledgeDocument(
    id='autosar_cpp14_rules',
    title='AUTOSAR C++14 证据化审计规则',
    category=KnowledgeCategory.COMPLIANCE,
    tags=[
        'autosar',
        'autosar_cpp14',
        'cpp',
        'automotive',
        'misra',
        'cert',
        'evidence_chain',
    ],
    severity='medium',
    content="""
生产审计原则
- 不把单条工具命中直接升级为漏洞；必须绑定真实文件、行号、调用入口、上下文约束和反例检查。
- 对每个 finding 给出 evidence_chain：入口/调用者、被审计语句、边界条件、资源生命周期、失败路径和影响点。
- 缺少调用链、宏/配置条件、对象生命周期或边界条件时，结论应为 uncertain，而不是 confirmed。

AUTOSAR C++14 重点
- 动态内存、异常、RTTI、隐式转换、未受控递归和非确定性行为要结合运行上下文判断。
- 指针/引用、数组、span-like 缓冲区、整数转换和所有权转移必须确认来源、长度、生命周期和空值约束。
- 不安全 C API 命中只能作为候选点；若已有上游长度约束、固定枚举输入或封装契约，应降级或标注反例。
- 共享状态、static/global 变量、volatile 和 atomics 必须结合 OS task、ISR、锁/临界区覆盖范围判断。
""".strip(),
)
