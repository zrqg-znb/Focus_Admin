from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Any

from apps.deepaudit.config_resolver import resolve_embedding_config
from apps.deepaudit.rag.embeddings import EmbeddingService
from apps.deepaudit.rag.indexer import CodeIndexer
from apps.deepaudit.rag.retriever import CodeRetriever, RetrievalResult
from apps.deepaudit.storage import VECTOR_DB_DIR, ensure_storage_dirs

logger = logging.getLogger(__name__)


class ProjectCodeRetriever:
    """
    项目级 RAG 封装。

    负责：
    - 统一读取 Focus 本地 embedding 配置
    - 统一向量库存储目录
    - 懒初始化索引与检索器
    - 在 embedding/索引不可用时返回可理解的降级原因
    """

    def __init__(
        self,
        *,
        project_root: str,
        user_config: dict[str, Any] | None = None,
        project_id: str | None = None,
        project_name: str | None = None,
        exclude_patterns: list[str] | None = None,
        target_files: list[str] | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.user_config = user_config or {}
        self.project_id = str(project_id or "").strip() or None
        self.project_name = str(project_name or "").strip() or self.project_root.name
        self.exclude_patterns = [str(item).strip() for item in (exclude_patterns or []) if str(item).strip()]
        self.target_files = [str(item).strip() for item in (target_files or []) if str(item).strip()]

        ensure_storage_dirs()
        self.persist_directory = str(VECTOR_DB_DIR)
        self.collection_name = self._build_collection_name()

        self._lock = asyncio.Lock()
        self._ready = False
        self._unavailable_reason: str | None = None
        self._embedding_service: EmbeddingService | None = None
        self._indexer: CodeIndexer | None = None
        self._retriever: CodeRetriever | None = None

    def _build_collection_name(self) -> str:
        base = self.project_id or self.project_name or self.project_root.name or "workspace"
        base = re.sub(r"[^a-zA-Z0-9_]+", "_", base).strip("_").lower() or "workspace"
        scope_seed = "||".join(sorted(self.target_files)) or "__all__"
        exclude_seed = "||".join(sorted(self.exclude_patterns))
        scope_hash = hashlib.sha1(f"{scope_seed}::{exclude_seed}".encode("utf-8")).hexdigest()[:12]
        return f"deepaudit_{base}_{scope_hash}"

    def get_unavailable_reason(self) -> str | None:
        return self._unavailable_reason

    def _embedding_unavailable_reason(self) -> str | None:
        embedding_config = resolve_embedding_config(self.user_config)
        provider = embedding_config.get("provider") or "openai"
        if provider != "ollama" and not str(embedding_config.get("api_key") or "").strip():
            return (
                f"当前未配置可用的 embedding API Key（provider={provider}, "
                f"model={embedding_config.get('model') or 'default'}），RAG 语义检索已自动降级。"
            )
        return None

    async def _ensure_ready(self) -> None:
        if self._ready or self._unavailable_reason:
            return
        async with self._lock:
            if self._ready or self._unavailable_reason:
                return

            if not self.project_root.exists():
                self._unavailable_reason = f"项目目录不存在: {self.project_root}"
                return

            unavailable_reason = self._embedding_unavailable_reason()
            if unavailable_reason:
                self._unavailable_reason = unavailable_reason
                logger.info("[ProjectCodeRetriever] %s", unavailable_reason)
                return

            try:
                embedding_config = resolve_embedding_config(self.user_config)
                self._embedding_service = EmbeddingService(
                    provider=embedding_config.get("provider"),
                    model=embedding_config.get("model"),
                    api_key=embedding_config.get("api_key"),
                    base_url=embedding_config.get("base_url"),
                    dimension=embedding_config.get("dimensions"),
                    user_config=self.user_config,
                )
                self._indexer = CodeIndexer(
                    collection_name=self.collection_name,
                    embedding_service=self._embedding_service,
                    persist_directory=self.persist_directory,
                )
                self._retriever = CodeRetriever(
                    collection_name=self.collection_name,
                    embedding_service=self._embedding_service,
                    persist_directory=self.persist_directory,
                    api_key=embedding_config.get("api_key"),
                )

                progress_count = 0
                async for progress in self._indexer.smart_index_directory(
                    directory=str(self.project_root),
                    exclude_patterns=self.exclude_patterns,
                    include_patterns=self.target_files or None,
                ):
                    progress_count += 1
                    if progress_count <= 3 or progress_count % 25 == 0:
                        logger.info(
                            "[ProjectCodeRetriever] indexing %s: %s/%s files, %s chunks",
                            self.collection_name,
                            progress.processed_files,
                            progress.total_files,
                            progress.total_chunks,
                        )

                await self._retriever.initialize()
                self._ready = True
                logger.info(
                    "[ProjectCodeRetriever] ready: collection=%s project=%s",
                    self.collection_name,
                    self.project_root,
                )
            except Exception as exc:
                self._unavailable_reason = f"项目代码索引初始化失败: {exc}"
                logger.warning(
                    "[ProjectCodeRetriever] failed to initialize collection=%s: %s",
                    self.collection_name,
                    exc,
                    exc_info=True,
                )

    async def _get_retriever(self) -> CodeRetriever:
        await self._ensure_ready()
        if self._unavailable_reason or not self._retriever:
            raise RuntimeError(self._unavailable_reason or "RAG 检索器尚未初始化")
        return self._retriever

    async def retrieve(
        self,
        *,
        query: str,
        top_k: int = 10,
        filter_file_path: str | None = None,
        filter_language: str | None = None,
    ) -> list[RetrievalResult]:
        retriever = await self._get_retriever()
        return await retriever.retrieve(
            query=query,
            top_k=top_k,
            filter_file_path=filter_file_path,
            filter_language=filter_language,
        )

    async def retrieve_security_related(
        self,
        *,
        vulnerability_type: str | None = None,
        top_k: int = 20,
    ) -> list[RetrievalResult]:
        retriever = await self._get_retriever()
        return await retriever.retrieve_security_related(
            vulnerability_type=vulnerability_type,
            top_k=top_k,
        )

    async def retrieve_function_context(
        self,
        *,
        function_name: str,
        file_path: str | None = None,
        include_callers: bool = True,
        include_callees: bool = True,
        top_k: int = 10,
    ) -> dict[str, list[RetrievalResult]]:
        retriever = await self._get_retriever()
        return await retriever.retrieve_function_context(
            function_name=function_name,
            file_path=file_path,
            include_callers=include_callers,
            include_callees=include_callees,
            top_k=top_k,
        )
