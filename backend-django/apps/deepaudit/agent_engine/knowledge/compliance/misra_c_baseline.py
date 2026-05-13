"""MISRA C 基线检查"""

from ..base import KnowledgeCategory, KnowledgeDocument


MISRA_C_BASELINE = KnowledgeDocument(
    id='misra_c_baseline',
    title='MISRA C 基线检查',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['misra', 'misra_c', 'c', 'embedded', 'automotive', 'safety', 'coding_standard'],
    severity='low',
    content="""
检查重点
- 是否存在未定义行为、隐藏副作用、可疑类型转换和不受控的宏展开
- 是否保持接口清晰、全局状态最小化、可读性和可维护性
- 是否对警告、静态分析和规范偏差有明确的说明和跟踪

落地建议
- 结合项目自己的 MISRA 偏差清单和代码审核流程使用，不要机械套模板
- 重点关注初始化、表达式副作用、控制流、整数提升和指针别名问题
- 对汽车底层模块建议把规范检查和单元测试一起纳入交付门禁
""".strip(),
)
