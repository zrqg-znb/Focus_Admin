"""
缓冲区溢出知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


BUFFER_OVERFLOW = KnowledgeDocument(
    id="vuln_buffer_overflow",
    title="Buffer Overflow",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "memory", "bounds", "embedded", "mcu"],
    severity="critical",
    cwe_ids=["CWE-120", "CWE-121", "CWE-122"],
    content="""
典型信号:
- strcpy/strcat/sprintf/gets/scanf("%s")
- memcpy/memmove 长度由外部输入控制
- 固定长度栈缓冲区与可变长度输入组合

审计清单:
1. 目标缓冲区大小是否明确且与长度参数匹配
2. 长度值是否可能溢出、截断或为负后转换
3. 是否缺失 NUL 终止、边界检查或最大长度限制
4. 宏、结构体字段和 ISR/任务上下文是否改变真实容量

修复思路:
- 优先使用 snprintf / strlcpy / strlcat 或显式边界检查
- 把容量和实际写入长度一起传递并校验
- 对外部输入做长度上限和编码约束

Harness 建议:
- 为长度边界值、超长输入和格式化字符串输入构造测试
- 使用 ASan/UBSan 观察越界写、栈破坏和无效访问
""",
)
