"""
资源泄漏知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


RESOURCE_LEAK = KnowledgeDocument(
    id="vuln_resource_leak",
    title="Resource Leak",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "resource", "leak", "file", "lock"],
    severity="medium",
    cwe_ids=["CWE-401", "CWE-772"],
    content="""
典型信号:
- malloc/new/open/lock 成功后在部分错误路径未释放
- 早返回、goto、异常风格分支破坏对称释放
- MCU 外设句柄、DMA、互斥锁、文件句柄未回收

审计清单:
1. 成功路径和失败路径是否都能释放资源
2. 锁、文件、内存、硬件资源是否统一 cleanup
3. 是否存在重入路径导致资源泄漏或状态卡死

修复思路:
- 使用单一出口 cleanup 块或 RAII
- 让所有资源拥有明确所有者
- 记录 acquire/release 对，防止异常路径漏掉
""",
)
