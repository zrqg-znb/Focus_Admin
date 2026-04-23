"""
释放后使用知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


USE_AFTER_FREE = KnowledgeDocument(
    id="vuln_use_after_free",
    title="Use After Free",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "uaf", "heap", "lifetime"],
    severity="critical",
    cwe_ids=["CWE-416", "CWE-415"],
    content="""
典型信号:
- free/delete 之后继续解引用、写入或传递指针
- 释放后仍保留在全局、缓存、回调或链表中
- 错误路径与正常路径混合导致重复释放或悬空指针

审计清单:
1. 谁拥有资源，谁负责释放
2. 是否存在别名指针、容器引用或异步回调
3. 释放后是否立即置空或从共享结构中移除
4. 错误恢复路径是否会再次进入释放逻辑

修复思路:
- 明确所有权，释放后立即失效引用
- 使用 RAII/智能指针或统一 cleanup 块
- 对共享资源加生命周期状态检查

Harness 建议:
- 复制目标函数和最小依赖，构造释放后访问路径
- 用 ASan 检查 heap-use-after-free 与 double-free
""",
)
