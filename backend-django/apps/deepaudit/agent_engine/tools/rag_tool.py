"""
RAG 检索工具
支持语义检索代码
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from pydantic import BaseModel, Field

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)

_SEARCH_CODE_TOOL_NAME = "search_code"
_MAX_FALLBACK_KEYWORDS = 5
_QUERY_TOKEN_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_:]{2,}\b")
_COMMON_QUERY_STOPWORDS = {
    "and",
    "are",
    "code",
    "context",
    "find",
    "for",
    "from",
    "function",
    "functions",
    "how",
    "implement",
    "implementation",
    "into",
    "logic",
    "main",
    "maybe",
    "need",
    "path",
    "paths",
    "query",
    "search",
    "show",
    "that",
    "the",
    "this",
    "use",
    "used",
    "using",
    "where",
    "with",
}
_C_FAMILY_QUERY_HINTS: tuple[tuple[re.Pattern[str], list[str]], ...] = (
    (
        re.compile(r"(buffer|overflow|越界|边界|copy|拷贝|string|字符串|格式化)", re.IGNORECASE),
        ["strcpy", "strcat", "sprintf", "snprintf", "memcpy", "memmove"],
    ),
    (
        re.compile(r"(free|uaf|use.?after.?free|double.?free|leak|泄露|内存|memory|alloc)", re.IGNORECASE),
        ["malloc", "calloc", "realloc", "free", "new", "delete"],
    ),
    (
        re.compile(r"(format|string|printf|格式化)", re.IGNORECASE),
        ["printf", "fprintf", "sprintf", "snprintf", "vsprintf"],
    ),
    (
        re.compile(r"(race|deadlock|lock|mutex|thread|concurrency|并发|竞态|死锁|锁)", re.IGNORECASE),
        ["mutex", "lock", "unlock", "pthread", "std::thread", "atomic"],
    ),
    (
        re.compile(r"(interrupt|isr|irq|critical|中断|临界区)", re.IGNORECASE),
        ["ISR", "interrupt", "IRQ", "taskENTER_CRITICAL", "taskEXIT_CRITICAL"],
    ),
    (
        re.compile(r"(null|nullptr|空指针)", re.IGNORECASE),
        ["NULL", "nullptr"],
    ),
)


def _dedupe_keywords(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        keyword = str(value or "").strip()
        if not keyword:
            continue
        lowered = keyword.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered.append(keyword)
    return ordered


def _normalize_directory(file_path: str | None) -> str | None:
    normalized = str(file_path or "").strip().replace("\\", "/").strip("/")
    if not normalized:
        return None
    if "/" not in normalized:
        return None
    return normalized.rsplit("/", 1)[0] or None


def _extract_query_keywords(query: str) -> list[str]:
    candidates: list[str] = []
    text = str(query or "").strip()
    if not text:
        return []

    for match in _QUERY_TOKEN_PATTERN.findall(text):
        token = match.strip()
        lowered = token.lower()
        if lowered in _COMMON_QUERY_STOPWORDS:
            continue
        if len(token) < 3:
            continue
        candidates.append(token)

    for pattern, mapped_keywords in _C_FAMILY_QUERY_HINTS:
        if pattern.search(text):
            candidates.extend(mapped_keywords)

    return _dedupe_keywords(candidates)[:_MAX_FALLBACK_KEYWORDS]


def _extract_function_keywords(function_name: str) -> list[str]:
    candidates = _extract_query_keywords(function_name)
    lowered_name = str(function_name or "").strip().lower()
    if not lowered_name:
        return candidates
    for pattern, mapped_keywords in _C_FAMILY_QUERY_HINTS:
        if pattern.search(lowered_name):
            candidates.extend(mapped_keywords)
    return _dedupe_keywords([function_name, *candidates])[:_MAX_FALLBACK_KEYWORDS]


class _KeywordFallbackMixin:
    def __init__(
        self,
        *,
        search_tool: AgentTool | None = None,
        enable_keyword_fallback: bool = False,
    ) -> None:
        self._search_tool = search_tool
        self._enable_keyword_fallback = bool(enable_keyword_fallback and search_tool is not None)
        self._cached_unavailable_reason: str | None = None

    def _mark_retriever_unavailable(self, reason: str) -> None:
        normalized = str(reason or "").strip()
        if normalized:
            self._cached_unavailable_reason = normalized

    def _current_unavailable_reason(self) -> str | None:
        if self._cached_unavailable_reason:
            return self._cached_unavailable_reason
        unavailable_reason = getattr(self.retriever, "get_unavailable_reason", lambda: None)()
        normalized = str(unavailable_reason or "").strip()
        if normalized:
            self._cached_unavailable_reason = normalized
            return normalized
        return None

    def _supports_keyword_fallback(self) -> bool:
        return self._enable_keyword_fallback and self._search_tool is not None

    async def _execute_keyword_fallback(
        self,
        *,
        base_message: str,
        reason: str,
        reason_category: str,
        keywords: list[str],
        file_path: str | None = None,
        max_results: int = 20,
    ) -> ToolResult | None:
        if not self._supports_keyword_fallback():
            return None

        fallback_keywords = _dedupe_keywords(keywords)[:_MAX_FALLBACK_KEYWORDS]
        if not fallback_keywords:
            return ToolResult(
                success=True,
                data=f"{base_message}\n降级原因: {reason}\n未能提取有效关键词，请改用 read_file 或 list_files 手动定位代码。",
                metadata={
                    "degraded": True,
                    "degraded_tool": _SEARCH_CODE_TOOL_NAME,
                    "fallback_reason": reason,
                    "fallback_reason_category": reason_category,
                    "fallback_keywords": [],
                    "results_count": 0,
                },
            )

        max_results_per_keyword = max(5, min(10, max_results // max(1, len(fallback_keywords))))
        search_directory = _normalize_directory(file_path)
        output_parts = [
            base_message,
            f"降级原因: {reason}",
            f"关键词: {', '.join(fallback_keywords)}",
        ]
        total_matches = 0

        for keyword in fallback_keywords:
            search_result = await self._search_tool.execute(
                keyword=keyword,
                directory=search_directory,
                case_sensitive=False,
                max_results=max_results_per_keyword,
                is_regex=False,
            )
            if not search_result.success:
                output_parts.append(f"\n=== 关键词 {keyword} ===\n搜索失败: {search_result.error}")
                continue

            total_matches += int(search_result.metadata.get("matches") or 0)
            search_output = str(search_result.data or "").strip()
            if search_output:
                output_parts.append(f"\n=== 关键词 {keyword} ===\n{search_output}")

        return ToolResult(
            success=True,
            data="\n".join(output_parts),
            metadata={
                "degraded": True,
                "degraded_tool": _SEARCH_CODE_TOOL_NAME,
                "fallback_reason": reason,
                "fallback_reason_category": reason_category,
                "fallback_keywords": fallback_keywords,
                "results_count": total_matches,
            },
        )


class RAGQueryInput(BaseModel):
    """RAG 查询输入参数"""
    query: str = Field(description="搜索查询，描述你要找的代码功能或特征")
    top_k: int = Field(default=10, description="返回结果数量")
    file_path: Optional[str] = Field(default=None, description="限定搜索的文件路径")
    language: Optional[str] = Field(default=None, description="限定编程语言")
    

class RAGQueryTool(_KeywordFallbackMixin, AgentTool):
    """
    RAG 代码检索工具
    使用语义搜索在代码库中查找相关代码
    """
    
    def __init__(
        self,
        retriever: Any,
        *,
        search_tool: AgentTool | None = None,
        enable_keyword_fallback: bool = False,
    ):
        AgentTool.__init__(self)
        self.retriever = retriever
        _KeywordFallbackMixin.__init__(
            self,
            search_tool=search_tool,
            enable_keyword_fallback=enable_keyword_fallback,
        )
    
    @property
    def name(self) -> str:
        return "rag_query"
    
    @property
    def description(self) -> str:
        return """在代码库中进行语义搜索。
使用场景:
- 查找特定功能的实现代码
- 查找调用某个函数的代码
- 查找处理用户输入的代码
- 查找数据库操作相关代码
- 查找认证/授权相关代码

输入: 
- query: 描述你要查找的代码，例如 "处理用户登录的函数"、"SQL查询执行"、"文件上传处理"
- top_k: 返回结果数量（默认10）
- file_path: 可选，限定在某个文件中搜索
- language: 可选，限定编程语言

输出: 相关的代码片段列表，包含文件路径、行号、代码内容和相似度分数"""
    
    @property
    def args_schema(self):
        return RAGQueryInput
    
    async def _execute(
        self,
        query: str,
        top_k: int = 10,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        **kwargs
    ) -> ToolResult:
        """执行 RAG 检索"""
        try:
            unavailable_reason = self._current_unavailable_reason()
            if unavailable_reason:
                degraded = await self.execute_degraded_fallback(
                    reason=unavailable_reason,
                    reason_category="unavailable",
                    query=query,
                    top_k=top_k,
                    file_path=file_path,
                    language=language,
                )
                if degraded is not None:
                    return degraded
                return ToolResult(
                    success=True,
                    data=f"RAG 当前不可用: {unavailable_reason}",
                    metadata={"query": query, "results_count": 0, "degraded": True},
                )

            results = await self.retriever.retrieve(
                query=query,
                top_k=top_k,
                filter_file_path=file_path,
                filter_language=language,
            )
            
            if not results:
                return ToolResult(
                    success=True,
                    data="没有找到相关代码",
                    metadata={"query": query, "results_count": 0}
                )
            
            # 格式化输出
            output_parts = [f"找到 {len(results)} 个相关代码片段:\n"]
            
            for i, result in enumerate(results):
                output_parts.append(f"\n--- 结果 {i+1} (相似度: {result.score:.2f}) ---")
                output_parts.append(f"文件: {result.file_path}")
                output_parts.append(f"行号: {result.line_start}-{result.line_end}")
                if result.name:
                    output_parts.append(f"名称: {result.name}")
                if result.security_indicators:
                    output_parts.append(f"安全指标: {', '.join(result.security_indicators)}")
                semantic_lines = []
                for key, label in (
                    ("module_layers", "模块层级"),
                    ("autosar_api_calls", "AUTOSAR/BSW/MCAL API"),
                    ("task_isr_contexts", "Task/ISR 上下文"),
                    ("shared_resources", "共享资源"),
                    ("sync_primitives", "同步/临界区"),
                    ("macro_config_conditions", "宏/配置条件"),
                    ("call_graph_callees", "被调函数"),
                    ("symbol_definitions", "符号定义"),
                    ("include_dependencies", "Include 依赖"),
                    ("android_components", "Android 组件"),
                    ("android_entrypoints", "Android 入口方法"),
                    ("android_ipc_calls", "Binder/IPC 线索"),
                    ("android_permission_identity_checks", "权限/身份校验"),
                    ("android_intent_usage", "Intent/组件调用"),
                    ("android_pending_intent_usage", "PendingIntent/DeepLink"),
                    ("android_webview_usage", "WebView/JSBridge"),
                    ("android_jni_usage", "JNI/Native 边界"),
                    ("android_storage_privacy_usage", "存储/日志/隐私"),
                    ("android_hmi_display_usage", "HMI/显示链路"),
                    ("android_crypto_network_usage", "加密/网络配置"),
                    ("android_privapp_platform_usage", "特权应用/平台权限"),
                    ("android_vehicle_diagnostics_usage", "车载诊断/总线"),
                    ("android_ota_update_usage", "OTA/升级链路"),
                    ("android_vehicle_hal_usage", "Vehicle HAL/CarService"),
                    ("java_runtime_reflection_usage", "Java 反射/运行时"),
                    ("java_parser_serialization_usage", "Java 解析/反序列化"),
                    ("android_manifest_components", "Manifest 组件"),
                    ("android_manifest_exported", "Manifest exported"),
                    ("android_manifest_permissions", "Manifest 权限"),
                    ("android_intent_filters", "Manifest intent-filter"),
                    ("android_provider_authorities", "Provider authority"),
                    ("android_network_security_config", "Network Security Config"),
                    ("android_privapp_permissions", "Privapp 权限配置"),
                    ("android_selinux_policy", "SELinux 策略"),
                    ("android_vehicle_config", "车机/诊断配置"),
                ):
                    values = result.metadata.get(key)
                    if isinstance(values, list) and values:
                        semantic_lines.append(f"{label}: {', '.join(str(item) for item in values[:8])}")
                    elif values:
                        semantic_lines.append(f"{label}: {values}")
                if semantic_lines:
                    output_parts.append("工程语义线索:")
                    output_parts.extend(f"- {line}" for line in semantic_lines)
                output_parts.append(f"代码:\n```{result.language}\n{result.content}\n```")
            
            return ToolResult(
                success=True,
                data="\n".join(output_parts),
                metadata={
                    "query": query,
                    "results_count": len(results),
                    "results": [r.to_dict() for r in results],
                }
            )
            
        except Exception as e:
            self._mark_retriever_unavailable(str(e))
            degraded = await self.execute_degraded_fallback(
                reason=str(e),
                reason_category="error",
                query=query,
                top_k=top_k,
                file_path=file_path,
                language=language,
            )
            if degraded is not None:
                logger.warning("RAG query degraded to keyword search: %s", e)
                return degraded
            return ToolResult(
                success=False,
                error=f"RAG 检索失败: {str(e)}",
            )

    async def execute_degraded_fallback(
        self,
        *,
        reason: str,
        reason_category: str,
        query: str,
        top_k: int = 10,
        file_path: Optional[str] = None,
        language: Optional[str] = None,
        **_kwargs,
    ) -> ToolResult | None:
        self._mark_retriever_unavailable(reason)
        keywords = _extract_query_keywords(query)
        if language and str(language).strip().lower() in {"c", "cpp"}:
            keywords.extend(["strcpy", "memcpy"])
        if language and str(language).strip().lower() in {"java", "kotlin"}:
            keywords.extend(["Intent", "WebView", "Binder", "AndroidManifest"])
        return await self._execute_keyword_fallback(
            base_message="RAG 不可用，已切换为关键词搜索。",
            reason=reason,
            reason_category=reason_category,
            keywords=keywords,
            file_path=file_path,
            max_results=max(top_k * 2, 10),
        )


class SecurityCodeSearchInput(BaseModel):
    """安全代码搜索输入"""
    vulnerability_type: str = Field(
        description="漏洞类型: sql_injection, xss, command_injection, path_traversal, ssrf, deserialization, auth_bypass, hardcoded_secret"
    )
    top_k: int = Field(default=20, description="返回结果数量")


class SecurityCodeSearchTool(AgentTool):
    """
    安全相关代码搜索工具
    专门用于查找可能存在安全漏洞的代码
    """
    
    def __init__(self, retriever: Any):
        super().__init__()
        self.retriever = retriever
    
    @property
    def name(self) -> str:
        return "security_code_search"
    
    @property
    def description(self) -> str:
        return """搜索可能存在安全漏洞的代码。
专门针对特定漏洞类型进行搜索。

支持的漏洞类型:
- sql_injection: SQL 注入
- xss: 跨站脚本
- command_injection: 命令注入
- path_traversal: 路径遍历
- ssrf: 服务端请求伪造
- deserialization: 不安全的反序列化
- auth_bypass: 认证绕过
- hardcoded_secret: 硬编码密钥"""
    
    @property
    def args_schema(self):
        return SecurityCodeSearchInput
    
    async def _execute(
        self,
        vulnerability_type: Optional[str] = None,
        top_k: int = 20,
        **kwargs
    ) -> ToolResult:
        """执行安全代码搜索"""
        try:
            normalized_vulnerability_type = str(vulnerability_type or "").strip() or "security"
            unavailable_reason = getattr(self.retriever, "get_unavailable_reason", lambda: None)()
            if unavailable_reason:
                return ToolResult(
                    success=True,
                    data=f"安全代码搜索已降级: {unavailable_reason}",
                    metadata={
                        "vulnerability_type": normalized_vulnerability_type,
                        "results_count": 0,
                        "degraded": True,
                    },
                )

            results = await self.retriever.retrieve_security_related(
                vulnerability_type=vulnerability_type,
                top_k=top_k,
            )
            
            if not results:
                return ToolResult(
                    success=True,
                    data=f"没有找到与 {normalized_vulnerability_type} 相关的代码",
                    metadata={"vulnerability_type": normalized_vulnerability_type, "results_count": 0}
                )
            
            # 格式化输出
            output_parts = [f"找到 {len(results)} 个可能与 {normalized_vulnerability_type} 相关的代码:\n"]
            
            for i, result in enumerate(results):
                output_parts.append(f"\n--- 可疑代码 {i+1} ---")
                output_parts.append(f"文件: {result.file_path}:{result.line_start}")
                if result.security_indicators:
                    output_parts.append(f"⚠️ 安全指标: {', '.join(result.security_indicators)}")
                output_parts.append(f"代码:\n```{result.language}\n{result.content}\n```")
            
            return ToolResult(
                success=True,
                data="\n".join(output_parts),
                metadata={
                    "vulnerability_type": normalized_vulnerability_type,
                    "results_count": len(results),
                }
            )
            
        except Exception as e:
            error_msg = str(e)
            # 提供更友好的错误信息
            if "401" in error_msg or "Unauthorized" in error_msg:
                return ToolResult(
                    success=False,
                    error=f"安全代码搜索失败: API 认证失败（401 Unauthorized）。\n"
                          f"请检查系统配置中的 LLM API Key 是否正确设置。\n"
                          f"错误详情: {error_msg[:200]}",
                )
            elif "403" in error_msg or "Forbidden" in error_msg:
                return ToolResult(
                    success=False,
                    error=f"安全代码搜索失败: API 访问被拒绝（403 Forbidden）。\n"
                          f"请检查 API Key 是否有足够的权限。\n"
                          f"错误详情: {error_msg[:200]}",
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"安全代码搜索失败: {error_msg[:500]}",
                )


class FunctionContextInput(BaseModel):
    """函数上下文搜索输入"""
    function_name: str = Field(description="函数名称")
    file_path: Optional[str] = Field(default=None, description="文件路径")
    include_callers: bool = Field(default=True, description="是否包含调用者")
    include_callees: bool = Field(default=True, description="是否包含被调用的函数")


class FunctionContextTool(_KeywordFallbackMixin, AgentTool):
    """
    函数上下文搜索工具
    查找函数的定义、调用者和被调用者
    """
    
    def __init__(
        self,
        retriever: Any,
        *,
        search_tool: AgentTool | None = None,
        enable_keyword_fallback: bool = False,
    ):
        AgentTool.__init__(self)
        self.retriever = retriever
        _KeywordFallbackMixin.__init__(
            self,
            search_tool=search_tool,
            enable_keyword_fallback=enable_keyword_fallback,
        )
    
    @property
    def name(self) -> str:
        return "function_context"
    
    @property
    def description(self) -> str:
        return """查找函数的上下文信息，包括定义、调用者和被调用的函数。
用于追踪数据流和理解函数的使用方式。

输入:
- function_name: 要查找的函数名
- file_path: 可选，限定文件路径
- include_callers: 是否查找调用此函数的代码
- include_callees: 是否查找此函数调用的其他函数"""
    
    @property
    def args_schema(self):
        return FunctionContextInput
    
    async def _execute(
        self,
        function_name: str,
        file_path: Optional[str] = None,
        include_callers: bool = True,
        include_callees: bool = True,
        **kwargs
    ) -> ToolResult:
        """执行函数上下文搜索"""
        try:
            unavailable_reason = self._current_unavailable_reason()
            if unavailable_reason:
                degraded = await self.execute_degraded_fallback(
                    reason=unavailable_reason,
                    reason_category="unavailable",
                    function_name=function_name,
                    file_path=file_path,
                    include_callers=include_callers,
                    include_callees=include_callees,
                )
                if degraded is not None:
                    return degraded
                return ToolResult(
                    success=True,
                    data=f"函数上下文检索已降级: {unavailable_reason}",
                    metadata={
                        "function_name": function_name,
                        "degraded": True,
                        "fallback_reason": unavailable_reason,
                    },
                )

            context = await self.retriever.retrieve_function_context(
                function_name=function_name,
                file_path=file_path,
                include_callers=include_callers,
                include_callees=include_callees,
            )
            
            output_parts = [f"函数 '{function_name}' 的上下文分析:\n"]
            
            # 函数定义
            if context["definition"]:
                output_parts.append("### 函数定义:")
                for result in context["definition"]:
                    output_parts.append(f"文件: {result.file_path}:{result.line_start}")
                    output_parts.append(f"```{result.language}\n{result.content}\n```")
            else:
                output_parts.append("未找到函数定义")
            
            # 调用者
            if context["callers"]:
                output_parts.append(f"\n### 调用此函数的代码 ({len(context['callers'])} 处):")
                for result in context["callers"][:5]:
                    output_parts.append(f"- {result.file_path}:{result.line_start}")
                    output_parts.append(f"```{result.language}\n{result.content[:500]}\n```")
            
            # 被调用者
            if context["callees"]:
                output_parts.append(f"\n### 此函数调用的其他函数:")
                for result in context["callees"][:5]:
                    if result.name:
                        output_parts.append(f"- {result.name} ({result.file_path})")
            
            return ToolResult(
                success=True,
                data="\n".join(output_parts),
                metadata={
                    "function_name": function_name,
                    "definition_count": len(context["definition"]),
                    "callers_count": len(context["callers"]),
                    "callees_count": len(context["callees"]),
                }
            )
            
        except Exception as e:
            self._mark_retriever_unavailable(str(e))
            degraded = await self.execute_degraded_fallback(
                reason=str(e),
                reason_category="error",
                function_name=function_name,
                file_path=file_path,
                include_callers=include_callers,
                include_callees=include_callees,
            )
            if degraded is not None:
                logger.warning("Function context degraded to keyword search: %s", e)
                return degraded
            return ToolResult(
                success=False,
                error=f"函数上下文搜索失败: {str(e)}",
            )

    async def execute_degraded_fallback(
        self,
        *,
        reason: str,
        reason_category: str,
        function_name: str,
        file_path: Optional[str] = None,
        include_callers: bool = True,
        include_callees: bool = True,
        **_kwargs,
    ) -> ToolResult | None:
        self._mark_retriever_unavailable(reason)
        keywords = _extract_function_keywords(function_name)
        if include_callers:
            keywords.extend(["call", "invoke"])
        if include_callees:
            keywords.extend(["malloc", "free", "lock", "unlock"])
        return await self._execute_keyword_fallback(
            base_message="RAG 函数上下文不可用，已切换为关键词搜索。",
            reason=reason,
            reason_category=reason_category,
            keywords=keywords,
            file_path=file_path,
            max_results=20,
        )
