"""
死锁知识
"""

from ..base import KnowledgeCategory, KnowledgeDocument


DEADLOCK = KnowledgeDocument(
    id="vuln_deadlock",
    title="Deadlock",
    category=KnowledgeCategory.VULNERABILITY,
    tags=["c", "cpp", "deadlock", "mutex", "rtos", "embedded"],
    severity="high",
    cwe_ids=["CWE-833"],
    content="""
典型信号:
- 多把锁嵌套且缺少统一顺序
- taskENTER_CRITICAL / mutex_lock 后有多分支 return
- ISR、任务、回调之间共享锁或等待条件交叉

审计清单:
1. 锁顺序是否一致
2. 每个退出分支是否都释放锁
3. ISR 上下文是否调用可能阻塞的 API
4. 条件变量、信号量、互斥锁是否存在循环等待

修复思路:
- 统一锁顺序并减少嵌套
- 缩短临界区
- ISR 与任务之间采用无阻塞同步策略
""",
)
