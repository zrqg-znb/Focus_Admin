"""
基于RAG的安全知识检索系统

利用现有的RAG模块实现安全知识的向量检索
"""

import json
import hashlib
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from apps.deepaudit.config_resolver import resolve_embedding_config
from apps.deepaudit import storage as deepaudit_storage

from .aliases import normalize_module_name, resolve_module_alias
from .base import KnowledgeDocument, KnowledgeCategory

logger = logging.getLogger(__name__)


class SecurityKnowledgeRAG:
    """
    安全知识RAG检索系统
    
    使用现有的RAG模块进行向量检索
    """
    
    COLLECTION_NAME = "security_knowledge"
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
    ):
        self.persist_directory = persist_directory or str(deepaudit_storage.VECTOR_DB_DIR)
        self._indexer = None
        self._retriever = None
        self._initialized = False
        self._builtin_signature = ""
        
        # 内置知识库 - 从模块化文件加载
        self._builtin_knowledge = self._load_builtin_knowledge()

    def reload_knowledge_sources(self) -> None:
        self._builtin_knowledge = self._load_builtin_knowledge()
    
    async def initialize(self):
        """初始化RAG组件"""
        if self._initialized:
            return
        
        try:
            from ...rag import CodeIndexer, CodeRetriever, EmbeddingService

            embedding_config = resolve_embedding_config(None)
            provider = str(embedding_config.get("provider") or "openai").strip().lower()
            api_key = str(embedding_config.get("api_key") or "").strip()
            if provider != "ollama" and not api_key:
                logger.info(
                    "SecurityKnowledgeRAG fallback enabled: embedding provider=%s has no API key",
                    provider,
                )
                self._initialized = True
                return

            embedding_service = EmbeddingService(
                provider=embedding_config.get("provider"),
                model=embedding_config.get("model"),
                api_key=embedding_config.get("api_key"),
                base_url=embedding_config.get("base_url"),
                dimension=embedding_config.get("dimensions"),
                user_config={},
            )
            
            self._indexer = CodeIndexer(
                collection_name=self.COLLECTION_NAME,
                embedding_service=embedding_service,
                persist_directory=self.persist_directory,
            )
            
            self._retriever = CodeRetriever(
                collection_name=self.COLLECTION_NAME,
                embedding_service=embedding_service,
                persist_directory=self.persist_directory,
            )
            
            await self._indexer.initialize()
            await self._retriever.initialize()
            
            # 检查是否需要索引或重建内置知识
            count = await self._indexer.get_chunk_count()
            collection_metadata = self._indexer.vector_store.get_collection_metadata() if self._indexer else {}
            stored_signature = str((collection_metadata or {}).get("knowledge_signature") or "").strip()
            if count == 0 or stored_signature != self._builtin_signature:
                if count > 0 and stored_signature != self._builtin_signature:
                    logger.info(
                        "SecurityKnowledgeRAG builtin signature changed, rebuilding knowledge index: %s -> %s",
                        stored_signature,
                        self._builtin_signature,
                    )
                    await self._indexer.vector_store.initialize(force_recreate=True)
                await self._index_builtin_knowledge()
            
            self._initialized = True
            logger.info("SecurityKnowledgeRAG initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize RAG: {e}, using fallback")
            self._initialized = True  # 标记为已初始化，使用fallback
    
    def _load_builtin_knowledge(self) -> List[KnowledgeDocument]:
        """从模块化文件加载内置安全知识"""
        all_docs = []
        
        # 加载漏洞知识
        try:
            from .vulnerabilities import ALL_VULNERABILITY_DOCS
            all_docs.extend(ALL_VULNERABILITY_DOCS)
            logger.debug(f"Loaded {len(ALL_VULNERABILITY_DOCS)} vulnerability docs")
        except ImportError as e:
            logger.warning(f"Failed to load vulnerability docs: {e}")
        
        # 加载框架知识
        try:
            from .frameworks import ALL_FRAMEWORK_DOCS
            all_docs.extend(ALL_FRAMEWORK_DOCS)
            logger.debug(f"Loaded {len(ALL_FRAMEWORK_DOCS)} framework docs")
        except ImportError as e:
            logger.warning(f"Failed to load framework docs: {e}")

        # 加载汽车 C / 嵌入式知识
        builtin_groups = [
            (".best_practices", "ALL_BEST_PRACTICE_DOCS"),
            (".code_patterns", "ALL_CODE_PATTERN_DOCS"),
            (".remediations", "ALL_REMEDIATION_DOCS"),
            (".compliance", "ALL_COMPLIANCE_DOCS"),
        ]
        for module_suffix, export_name in builtin_groups:
            try:
                module = __import__(
                    f"{__name__.rsplit('.', 1)[0]}{module_suffix}",
                    fromlist=[export_name],
                )
                docs = list(getattr(module, export_name) or [])
                all_docs.extend(docs)
                logger.debug("Loaded %s docs from %s", len(docs), module_suffix)
            except ImportError as e:
                logger.warning("Failed to load %s docs: %s", module_suffix, e)
            except Exception as e:
                logger.warning("Failed to inspect %s docs: %s", module_suffix, e)

        all_docs.extend(self._load_custom_knowledge())
        self._builtin_signature = self._compute_builtin_signature(all_docs)
        
        logger.info(f"Total knowledge documents loaded: {len(all_docs)}")
        return all_docs

    def _compute_builtin_signature(self, docs: List[KnowledgeDocument]) -> str:
        payload = [
            doc.to_dict()
            for doc in sorted(docs, key=lambda item: str(item.id or "").strip().lower())
        ]
        return hashlib.sha1(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _find_builtin_document(
        self,
        module_name: str,
        *,
        category: KnowledgeCategory | None = None,
    ) -> Optional[KnowledgeDocument]:
        module_name_normalized = normalize_module_name(module_name)
        resolved_module_name = resolve_module_alias(module_name)
        exact_candidates = {
            module_name_normalized,
            resolved_module_name,
            f"vuln_{module_name_normalized}",
            f"framework_{module_name_normalized}",
        }

        for doc in self._builtin_knowledge:
            if category and doc.category != category:
                continue
            doc_id = str(doc.id or "").strip().lower()
            if doc_id in exact_candidates:
                return doc

        for doc in self._builtin_knowledge:
            if category and doc.category != category:
                continue
            doc_id = str(doc.id or "").strip().lower()
            tags = {str(tag).strip().lower() for tag in (doc.tags or [])}
            if module_name_normalized and (
                module_name_normalized in doc_id
                or module_name_normalized in tags
                or any(module_name_normalized in tag for tag in tags)
            ):
                return doc
            if resolved_module_name and resolved_module_name in doc_id:
                return doc
        return None

    def _load_custom_knowledge(self) -> List[KnowledgeDocument]:
        ensure_dir = deepaudit_storage.KNOWLEDGE_DIR
        ensure_dir.mkdir(parents=True, exist_ok=True)
        custom_docs: List[KnowledgeDocument] = []
        for path in sorted(ensure_dir.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Failed to load custom knowledge file %s: %s", path, exc)
                continue

            category_name = str(raw.get("category") or KnowledgeCategory.BEST_PRACTICE.value).strip().lower()
            try:
                category = KnowledgeCategory(category_name)
            except ValueError:
                category = KnowledgeCategory.BEST_PRACTICE

            document_id = str(raw.get("id") or path.stem).strip() or path.stem
            title = str(raw.get("title") or document_id).strip() or document_id
            content = str(raw.get("content") or "").strip()
            if not content:
                continue

            custom_docs.append(
                KnowledgeDocument(
                    id=document_id,
                    title=title,
                    content=content,
                    category=category,
                    tags=[str(tag).strip() for tag in (raw.get("tags") or []) if str(tag).strip()],
                    severity=str(raw.get("severity") or "").strip() or None,
                    cwe_ids=[str(item).strip() for item in (raw.get("cwe_ids") or []) if str(item).strip()],
                    owasp_ids=[str(item).strip() for item in (raw.get("owasp_ids") or []) if str(item).strip()],
                    metadata={
                        **dict(raw.get("metadata") or {}),
                        "source": "custom",
                        "path": str(path),
                    },
                )
            )
        return custom_docs

    def _custom_doc_path(self, document_id: str) -> Path:
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(document_id or "").strip()).strip("_").lower() or "knowledge"
        deepaudit_storage.KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
        return deepaudit_storage.KNOWLEDGE_DIR / f"{slug}.json"
    
    async def _index_builtin_knowledge(self):
        """索引内置知识到向量数据库"""
        if not self._indexer:
            return
        
        logger.info("Indexing builtin security knowledge...")
        self.reload_knowledge_sources()
        
        # 转换为RAG可索引的格式
        files = []
        for doc in self._builtin_knowledge:
            files.append({
                "path": f"knowledge/{doc.category.value}/{doc.id}.md",
                "content": doc.to_embedding_text(),
            })
        
        async for progress in self._indexer.index_files(files, base_path="knowledge"):
            pass

        await self._indexer.vector_store.update_collection_metadata(
            {
                "knowledge_signature": self._builtin_signature,
                "knowledge_document_count": len(files),
            }
        )
        
        logger.info(f"Indexed {len(files)} knowledge documents")

    async def rebuild_index(self) -> Dict[str, Any]:
        self.reload_knowledge_sources()
        await self.initialize()
        if not self._indexer:
            stats = self.get_knowledge_stats()
            return {
                "enabled": False,
                "chunk_count": 0,
                "document_count": stats.get("total", 0),
            }

        await self._indexer.vector_store.initialize(force_recreate=True)
        files = [
            {
                "path": f"knowledge/{doc.category.value}/{doc.id}.md",
                "content": doc.to_embedding_text(),
            }
            for doc in self._builtin_knowledge
        ]
        async for _progress in self._indexer.index_files(files, base_path="knowledge"):
            pass
        await self._indexer.vector_store.update_collection_metadata(
            {
                "knowledge_signature": self._builtin_signature,
                "knowledge_document_count": len(self._builtin_knowledge),
            }
        )
        if self._retriever:
            await self._retriever.initialize()
        return {
            "enabled": True,
            "chunk_count": await self._indexer.get_chunk_count(),
            "document_count": len(self._builtin_knowledge),
        }

    async def get_index_status(self) -> Dict[str, Any]:
        self.reload_knowledge_sources()
        await self.initialize()
        if not self._indexer:
            stats = self.get_knowledge_stats()
            return {
                "enabled": False,
                "chunk_count": 0,
                "document_count": stats.get("total", 0),
            }
        return {
            "enabled": True,
            "chunk_count": await self._indexer.get_chunk_count(),
            "document_count": len(self._builtin_knowledge),
        }
    
    async def search(
        self,
        query: str,
        category: Optional[KnowledgeCategory] = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        搜索安全知识
        
        Args:
            query: 搜索查询
            category: 知识类别过滤
            top_k: 返回数量
            
        Returns:
            匹配的知识文档列表
        """
        self.reload_knowledge_sources()
        await self.initialize()
        
        # 如果RAG可用，使用向量检索
        if self._retriever:
            try:
                results = await self._retriever.retrieve(
                    query=query,
                    top_k=top_k,
                )
                
                return [
                    {
                        "id": r.chunk_id,
                        "content": r.content,
                        "score": r.score,
                        "file_path": r.file_path,
                    }
                    for r in results
                ]
            except Exception as e:
                logger.warning(f"RAG search failed: {e}, using fallback")
        
        # Fallback: 简单关键词匹配
        return self._fallback_search(query, category, top_k)
    
    def _fallback_search(
        self,
        query: str,
        category: Optional[KnowledgeCategory],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """简单的关键词匹配搜索（fallback）"""
        query_lower = query.lower()
        query_terms = query_lower.split()
        results = []
        
        for doc in self._builtin_knowledge:
            if category and doc.category != category:
                continue
            
            # 计算匹配分数
            score = 0
            content_lower = doc.content.lower()
            title_lower = doc.title.lower()
            
            # 标题匹配权重更高
            for term in query_terms:
                if term in title_lower:
                    score += 0.3
                if term in content_lower:
                    score += 0.1
            
            # 完整查询匹配
            if query_lower in title_lower:
                score += 0.5
            if query_lower in content_lower:
                score += 0.2
            
            # 标签匹配
            for tag in doc.tags:
                if query_lower in tag.lower() or any(t in tag.lower() for t in query_terms):
                    score += 0.15
            
            # CWE/OWASP匹配
            for cwe in doc.cwe_ids:
                if query_lower in cwe.lower():
                    score += 0.25
            for owasp in doc.owasp_ids:
                if query_lower in owasp.lower():
                    score += 0.25
            
            if score > 0:
                results.append({
                    "id": doc.id,
                    "title": doc.title,
                    "content": doc.content,
                    "category": doc.category.value,
                    "score": min(score, 1.0),
                    "tags": doc.tags,
                    "cwe_ids": doc.cwe_ids,
                    "severity": doc.severity,
                })
        
        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    async def get_vulnerability_knowledge(
        self,
        vuln_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定漏洞类型的知识
        
        Args:
            vuln_type: 漏洞类型（如sql_injection, xss等）
            
        Returns:
            漏洞知识文档
        """
        self.reload_knowledge_sources()
        # 标准化漏洞类型名称
        vuln_type_normalized = normalize_module_name(vuln_type)

        doc = self._find_builtin_document(vuln_type_normalized, category=KnowledgeCategory.VULNERABILITY)
        if doc:
            return doc.to_dict()
        
        # 使用搜索
        results = await self.search(vuln_type, top_k=1)
        return results[0] if results else None
    
    async def get_framework_knowledge(
        self,
        framework: str,
    ) -> Optional[Dict[str, Any]]:
        """
        获取特定框架的安全知识
        
        Args:
            framework: 框架名称（如fastapi, django等）
            
        Returns:
            框架安全知识文档
        """
        self.reload_knowledge_sources()
        framework_normalized = normalize_module_name(framework)

        doc = self._find_builtin_document(framework_normalized, category=KnowledgeCategory.FRAMEWORK)
        if doc:
            return doc.to_dict()
        
        # 使用搜索
        results = await self.search(framework, category=KnowledgeCategory.FRAMEWORK, top_k=1)
        return results[0] if results else None
    
    def get_all_vulnerability_types(self) -> List[str]:
        """获取所有支持的漏洞类型"""
        self.reload_knowledge_sources()
        return [
            doc.id.replace("vuln_", "")
            for doc in self._builtin_knowledge
            if doc.category == KnowledgeCategory.VULNERABILITY
        ]
    
    def get_all_frameworks(self) -> List[str]:
        """获取所有支持的框架"""
        self.reload_knowledge_sources()
        return [
            doc.id.replace("framework_", "")
            for doc in self._builtin_knowledge
            if doc.category == KnowledgeCategory.FRAMEWORK
        ]
    
    def get_knowledge_by_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """根据标签获取知识"""
        self.reload_knowledge_sources()
        results = []
        tags_lower = [t.lower() for t in tags]
        
        for doc in self._builtin_knowledge:
            doc_tags_lower = [t.lower() for t in doc.tags]
            if any(tag in doc_tags_lower for tag in tags_lower):
                results.append(doc.to_dict())
        
        return results
    
    def get_knowledge_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        self.reload_knowledge_sources()
        stats = {
            "total": len(self._builtin_knowledge),
            "by_category": {},
            "by_severity": {},
        }
        
        for doc in self._builtin_knowledge:
            cat = doc.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            
            if doc.severity:
                sev = doc.severity
                stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
        
        return stats

    def list_documents(
        self,
        *,
        category: str | None = None,
        keyword: str | None = None,
        tag: str | None = None,
    ) -> List[Dict[str, Any]]:
        self.reload_knowledge_sources()
        category_value = str(category or "").strip().lower()
        keyword_value = str(keyword or "").strip().lower()
        tag_value = str(tag or "").strip().lower()
        items: List[Dict[str, Any]] = []
        for doc in self._builtin_knowledge:
            if category_value and doc.category.value != category_value:
                continue
            if tag_value and tag_value not in {item.lower() for item in doc.tags}:
                continue
            if keyword_value:
                haystack = "\n".join([doc.id, doc.title, doc.content, " ".join(doc.tags)]).lower()
                if keyword_value not in haystack:
                    continue
            items.append(doc.to_dict())
        return items

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        self.reload_knowledge_sources()
        doc = self._find_builtin_document(document_id)
        if doc:
            return doc.to_dict()
        return None

    def save_custom_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        document_id = str(payload.get("id") or "").strip()
        if not document_id:
            document_id = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(payload.get("title") or "knowledge").strip()).strip("_").lower() or "knowledge"
        content = str(payload.get("content") or "").strip()
        if not content:
            raise ValueError("content 不能为空")

        document = {
            "id": document_id,
            "title": str(payload.get("title") or document_id).strip() or document_id,
            "content": content,
            "category": str(payload.get("category") or KnowledgeCategory.BEST_PRACTICE.value).strip().lower() or KnowledgeCategory.BEST_PRACTICE.value,
            "tags": [str(tag).strip() for tag in (payload.get("tags") or []) if str(tag).strip()],
            "severity": str(payload.get("severity") or "").strip() or None,
            "cwe_ids": [str(item).strip() for item in (payload.get("cwe_ids") or []) if str(item).strip()],
            "owasp_ids": [str(item).strip() for item in (payload.get("owasp_ids") or []) if str(item).strip()],
            "metadata": {
                **dict(payload.get("metadata") or {}),
                "source": "custom",
            },
        }
        path = self._custom_doc_path(document_id)
        path.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
        self.reload_knowledge_sources()
        return document

    def delete_custom_document(self, document_id: str) -> bool:
        path = self._custom_doc_path(document_id)
        if path.exists():
            path.unlink()
            self.reload_knowledge_sources()
            return True
        return False


# 全局实例
security_knowledge_rag = SecurityKnowledgeRAG()
