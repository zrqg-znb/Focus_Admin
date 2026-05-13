"""
知识模块系统 - 基于RAG的安全知识检索

提供专业的安全知识检索能力，支持：
- 漏洞类型知识（SQL注入、XSS、命令注入等）
- 框架安全知识（FastAPI、Django、Flask、Express等）
- 安全最佳实践
- 修复建议
- 代码模式识别

知识库采用模块化组织：
- vulnerabilities/: 漏洞类型知识
- frameworks/: 框架安全知识
- best_practices/: C/嵌入式最佳实践
- code_patterns/: C/嵌入式代码模式
- remediations/: 修复建议
- compliance/: 规范与合规检查
"""

# 基础定义
from .base import KnowledgeDocument, KnowledgeCategory
from .aliases import MODULE_ALIASES, normalize_module_name, resolve_module_alias

# 知识加载器
from .loader import (
    KnowledgeLoader,
    knowledge_loader,
    get_available_modules,
    get_module_content,
)

# RAG知识检索
from .rag_knowledge import (
    SecurityKnowledgeRAG,
    security_knowledge_rag,
)

from .best_practices import ALL_BEST_PRACTICE_DOCS
from .code_patterns import ALL_CODE_PATTERN_DOCS
from .remediations import ALL_REMEDIATION_DOCS
from .compliance import ALL_COMPLIANCE_DOCS

# 知识查询工具
from .tools import (
    SecurityKnowledgeQueryTool,
    GetVulnerabilityKnowledgeTool,
    ListKnowledgeModulesTool,
)

__all__ = [
    # 基础定义
    "KnowledgeDocument",
    "KnowledgeCategory",
    "MODULE_ALIASES",
    "normalize_module_name",
    "resolve_module_alias",
    
    # 知识加载器
    "KnowledgeLoader",
    "knowledge_loader",
    "get_available_modules",
    "get_module_content",
    
    # RAG知识检索
    "SecurityKnowledgeRAG",
    "security_knowledge_rag",

    # 汽车 C 知识包
    "ALL_BEST_PRACTICE_DOCS",
    "ALL_CODE_PATTERN_DOCS",
    "ALL_REMEDIATION_DOCS",
    "ALL_COMPLIANCE_DOCS",
    
    # 知识查询工具
    "SecurityKnowledgeQueryTool",
    "GetVulnerabilityKnowledgeTool",
    "ListKnowledgeModulesTool",
]
