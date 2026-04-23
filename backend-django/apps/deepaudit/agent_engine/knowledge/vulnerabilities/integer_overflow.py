"""
整数溢出知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


INTEGER_OVERFLOW = KnowledgeDocument(
    id="vuln_integer_overflow",
    title="Integer Overflow",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "integer", "overflow", "truncation", "size_t"],
    severity="high",
    cwe_ids=["CWE-190", "CWE-191", "CWE-680"],
    content="""
典型信号:
- 长度、索引、容量参与乘法/加法后再分配内存
- signed/unsigned 混用，负值转成大正数
- size_t/uint32_t/int16_t 之间截断

审计清单:
1. 算术结果是否参与内存分配、数组索引、循环边界
2. 外部输入是否直接进入长度或偏移计算
3. 设备寄存器/HAL 返回值是否存在符号扩展与截断

修复思路:
- 在算术前后做范围断言
- 使用 checked arithmetic 或更宽类型
- 避免把未经验证的 signed 值直接转成 size_t

Harness 建议:
- 覆盖 0、-1、最大值、临界值和 wrap-around 场景
- 开启 UBSan 观察 signed overflow 与 invalid shift
""",
)
