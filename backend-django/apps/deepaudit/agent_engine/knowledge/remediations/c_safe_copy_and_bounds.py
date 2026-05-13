"""安全拷贝与边界检查"""

from ..base import KnowledgeCategory, KnowledgeDocument


C_SAFE_COPY_AND_BOUNDS = KnowledgeDocument(
    id='c_safe_copy_and_bounds',
    title='安全拷贝与边界检查',
    category=KnowledgeCategory.REMEDIATION,
    tags=['c', 'embedded', 'automotive', 'bounds', 'copy', 'strcpy', 'sprintf', 'overflow'],
    severity='medium',
    content="""
典型问题
- strcpy / strcat / sprintf / vsprintf / gets / scanf("%s")
- memcpy / memmove / memset 的长度来自外部输入或未验证计算结果

修复建议
- 优先使用带长度上限的 API，并把目标缓冲区容量作为显式参数
- 拷贝前先验证源长度、目标容量和终止符空间
- 对长度计算、类型转换和整数运算做上界检查
- 不要把 strlen(src) 误当成目的缓冲区大小

落地方式
- 把危险 API 收敛到少量封装函数，统一做边界保护
- 为边界值、超长值、空串和截断路径增加测试
- 在汽车底层代码里特别留意固定长度栈缓冲区和诊断报文处理
""".strip(),
)
