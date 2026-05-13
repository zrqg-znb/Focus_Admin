"""
知识加载器 - 基于RAG的知识模块加载

将安全知识集成到Agent的系统提示词中
"""

import logging
from typing import List, Dict, Any, Optional

from .base import KnowledgeCategory
from .aliases import MODULE_ALIASES, normalize_module_name, resolve_module_alias

logger = logging.getLogger(__name__)


class KnowledgeLoader:
    """
    知识加载器
    
    负责将RAG检索的知识集成到Agent系统提示词中
    """
    
    def __init__(self, rag=None):
        # 延迟导入避免循环依赖
        if rag is None:
            from .rag_knowledge import security_knowledge_rag
            rag = security_knowledge_rag
        self._rag = rag
    
    async def load_module(self, module_name: str) -> str:
        """
        加载单个知识模块
        
        Args:
            module_name: 模块名称（如sql_injection, xss等）
            
        Returns:
            模块内容
        """
        knowledge = self._get_builtin_knowledge(module_name)
        if not knowledge:
            knowledge = await self._rag.get_vulnerability_knowledge(module_name)
        if knowledge:
            return knowledge.get("content", "")
        return ""
    
    async def load_modules(self, module_names: List[str]) -> Dict[str, str]:
        """
        批量加载知识模块
        
        Args:
            module_names: 模块名称列表
            
        Returns:
            模块名称到内容的映射
        """
        result = {}
        for name in module_names:
            content = await self.load_module(name)
            if content:
                result[name] = content
        return result
    
    async def search_knowledge(
        self,
        query: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        搜索相关知识
        
        Args:
            query: 搜索查询
            top_k: 返回数量
            
        Returns:
            相关知识列表
        """
        return await self._rag.search(query, top_k=top_k)
    
    def build_system_prompt_with_modules(
        self,
        base_prompt: str,
        module_names: List[str],
    ) -> str:
        """
        构建包含知识模块的系统提示词（同步版本，使用内置知识）
        
        Args:
            base_prompt: 基础系统提示词
            module_names: 要加载的模块名称列表
            
        Returns:
            增强后的系统提示词
        """
        if not module_names:
            return base_prompt
        
        # 使用内置知识（同步）
        knowledge_sections = []
        seen_documents: set[str] = set()
        for name in module_names:
            knowledge = self._get_builtin_knowledge(name)
            if knowledge and knowledge.get("id") not in seen_documents:
                seen_documents.add(str(knowledge.get("id") or ""))
                knowledge_sections.append(f"### {knowledge['title']}\n{knowledge['content']}")
        
        if not knowledge_sections:
            return base_prompt
        
        knowledge_text = "\n\n".join(knowledge_sections)
        
        return f"""{base_prompt}

---
## 专业安全知识参考

以下是与当前任务相关的安全知识，请在分析时参考：

{knowledge_text}

---
"""
    
    def _get_builtin_knowledge(self, module_name: str) -> Optional[Dict[str, Any]]:
        """获取内置知识（同步）"""
        module_name_normalized = normalize_module_name(module_name)
        resolved_module_name = resolve_module_alias(module_name)
        exact_candidates = {
            module_name_normalized,
            resolved_module_name,
            f"vuln_{module_name_normalized}",
            f"framework_{module_name_normalized}",
        }
        
        for doc in self._rag._builtin_knowledge:
            doc_id = str(doc.id or "").strip().lower()
            if doc_id in exact_candidates:
                return doc.to_dict()
        
        # 模糊匹配
        for doc in self._rag._builtin_knowledge:
            if module_name_normalized in doc.id or any(
                module_name_normalized in tag.lower() for tag in doc.tags
            ):
                return doc.to_dict()
            if resolved_module_name in str(doc.id or "").lower():
                return doc.to_dict()
        
        return None
    
    def get_available_modules(self) -> List[str]:
        """获取所有可用的知识模块"""
        return self.get_all_module_names()
    
    def get_all_module_names(self) -> List[str]:
        """获取所有模块名称（包括漏洞和框架）"""
        documents = self._rag.list_documents()
        module_names: List[str] = []
        seen = set()
        for document in documents:
            document_id = str((document or {}).get("id") or "").strip()
            if not document_id or document_id in seen:
                continue
            seen.add(document_id)
            module_names.append(document_id)
        return module_names
    
    def validate_modules(self, module_names: List[str]) -> Dict[str, List[str]]:
        """
        验证知识模块是否存在
        
        Args:
            module_names: 要验证的模块名称列表
            
        Returns:
            {"valid": [...], "invalid": [...]}
        """
        all_modules = self.get_all_module_names()
        all_modules_normalized = {normalize_module_name(m) for m in all_modules}
        ordered_modules = sorted(all_modules_normalized)
        
        valid = []
        invalid = []
        
        for name in module_names:
            name_normalized = normalize_module_name(name)
            resolved_name = normalize_module_name(MODULE_ALIASES.get(name_normalized, name_normalized))
            
            # 检查直接匹配
            if name_normalized in all_modules_normalized:
                valid.append(name_normalized)
            # 检查别名
            elif resolved_name in all_modules_normalized:
                valid.append(resolved_name)
            # 检查部分匹配
            elif any(name_normalized in m for m in ordered_modules):
                matched = next((m for m in ordered_modules if name_normalized in m), name_normalized)
                valid.append(matched)
            else:
                invalid.append(name)

        deduped_valid: list[str] = []
        seen: set[str] = set()
        for item in valid:
            normalized_item = normalize_module_name(item)
            if normalized_item in seen:
                continue
            seen.add(normalized_item)
            deduped_valid.append(item)

        return {"valid": deduped_valid, "invalid": invalid}


# 全局实例
knowledge_loader = KnowledgeLoader()


# 便捷函数
def get_available_modules() -> List[str]:
    """获取所有可用的知识模块"""
    return knowledge_loader.get_available_modules()


def get_module_content(module_name: str) -> Optional[str]:
    """获取模块内容（同步）"""
    knowledge = knowledge_loader._get_builtin_knowledge(module_name)
    return knowledge.get("content") if knowledge else None
