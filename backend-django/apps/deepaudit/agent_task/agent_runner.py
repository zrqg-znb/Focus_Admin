import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentFinding
from apps.deepaudit.agent_engine.agents import (
    AnalysisAgent,
    OrchestratorAgent,
    ReconAgent,
    VerificationAgent,
)
from apps.deepaudit.agent_engine.event_manager import AgentEventEmitter, EventManager


DEEPAUDIT_BACKEND_PATH = os.path.join(
    os.path.dirname(__file__),
    '../../../../DeepAudit/backend',
)
if DEEPAUDIT_BACKEND_PATH not in sys.path:
    sys.path.append(DEEPAUDIT_BACKEND_PATH)

logger = logging.getLogger(__name__)

try:
    from app.services.llm.service import LLMService, llm_service as default_llm_service
except ImportError:
    LLMService = None

    class MockLLMService:
        pass

    default_llm_service = MockLLMService()
    logger.warning("Original LLMService not found, using mock for compilation check")


PROVIDER_API_KEY_FIELDS = {
    "openai": "openaiApiKey",
    "gemini": "geminiApiKey",
    "claude": "claudeApiKey",
    "qwen": "qwenApiKey",
    "deepseek": "deepseekApiKey",
    "zhipu": "zhipuApiKey",
    "moonshot": "moonshotApiKey",
    "baidu": "baiduApiKey",
    "minimax": "minimaxApiKey",
    "doubao": "doubaoApiKey",
}
PROVIDER_DEFAULT_MODELS = {
    "openai": "gpt-5",
    "claude": "claude-sonnet-4.5",
    "gemini": "gemini-2.0-flash",
    "qwen": "qwen3-max-instruct",
    "deepseek": "deepseek-chat",
    "zhipu": "glm-4.6",
    "moonshot": "kimi-k2",
    "baidu": "ERNIE-4.0",
    "minimax": "abab6.5-chat",
    "doubao": "doubao-pro-32k",
    "ollama": "llama3.3",
}
LANGUAGE_BY_EXTENSION = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".swift": "swift",
    ".kt": "kotlin",
    ".m": "objective-c",
    ".mm": "objective-c++",
    ".sh": "shell",
    ".sql": "sql",
    ".vue": "vue",
}
SKIP_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
}
ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}


def _to_original_user_config(input_data: Dict[str, Any]) -> Dict[str, Any]:
    llm_config = dict(input_data.get("llm_config") or {})
    other_config = dict(input_data.get("other_config") or {})
    provider = str(llm_config.get("provider") or "openai").strip().lower() or "openai"
    api_key = str(llm_config.get("api_key") or "").strip()
    model = str(llm_config.get("model") or "").strip() or PROVIDER_DEFAULT_MODELS.get(provider, "")

    timeout_seconds = int(llm_config.get("timeout") or 150)
    llm_timeout_ms = timeout_seconds * 1000

    llm_payload = {
        "llmProvider": provider,
        "llmApiKey": api_key,
        "llmModel": model,
        "llmBaseUrl": str(llm_config.get("base_url") or "").strip(),
        "llmTimeout": llm_timeout_ms,
        "llmTemperature": llm_config.get("temperature"),
        "llmMaxTokens": llm_config.get("max_tokens"),
        "llmFirstTokenTimeout": llm_config.get("first_token_timeout"),
        "llmStreamTimeout": llm_config.get("stream_timeout"),
        "toolTimeout": llm_config.get("tool_timeout"),
        "subAgentTimeout": llm_config.get("sub_agent_timeout"),
        "agentTimeout": llm_config.get("agent_timeout"),
    }

    provider_api_field = PROVIDER_API_KEY_FIELDS.get(provider)
    if provider_api_field and api_key:
        llm_payload[provider_api_field] = api_key

    scan_config = dict(other_config.get("scan_config") or {})
    other_payload = {
        "outputLanguage": other_config.get("output_language"),
        "scanConfig": {
            "maxAnalyzeFiles": scan_config.get("max_analyze_files"),
            "llmConcurrency": scan_config.get("llm_concurrency"),
            "llmGapMs": scan_config.get("llm_gap_ms"),
            "includeTests": scan_config.get("include_tests"),
            "includeDocs": scan_config.get("include_docs"),
            "maxFileSize": scan_config.get("max_file_size"),
            "analysisDepth": scan_config.get("analysis_depth"),
        },
    }

    return {
        "llmConfig": {key: value for key, value in llm_payload.items() if value not in (None, "")},
        "otherConfig": {
            key: value
            for key, value in other_payload.items()
            if value not in (None, "", {})
        },
    }


def _build_llm_service(input_data: Dict[str, Any]):
    if LLMService is None:
        return default_llm_service
    return LLMService(user_config=_to_original_user_config(input_data))


def _collect_project_info(project_root: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    target_files = [
        str(item).strip()
        for item in (input_data.get("target_files") or [])
        if str(item).strip()
    ]
    file_count = 0
    languages: set[str] = set()
    collected_files: list[str] = []
    collected_dirs: set[str] = set()

    for current_root, dirs, files in os.walk(project_root):
        dirs[:] = [name for name in dirs if name not in SKIP_DIRECTORIES]
        relative_root = os.path.relpath(current_root, project_root)
        relative_root = "" if relative_root == "." else relative_root.replace("\\", "/")
        if relative_root:
            collected_dirs.add(relative_root)

        for file_name in files:
            relative_path = os.path.join(relative_root, file_name) if relative_root else file_name
            relative_path = relative_path.replace("\\", "/")
            file_count += 1
            extension = Path(file_name).suffix.lower()
            if extension in LANGUAGE_BY_EXTENSION:
                languages.add(LANGUAGE_BY_EXTENSION[extension])
            if len(collected_files) < 200:
                collected_files.append(relative_path)

    scope_limited = bool(target_files)
    structure = {
        "scope_limited": scope_limited,
        "scope_message": (
            f"当前任务仅审计指定的 {len(target_files)} 个目标文件。"
            if scope_limited
            else ""
        ),
        "files": target_files[:200] if scope_limited else collected_files[:200],
        "directories": sorted(collected_dirs)[:80],
    }

    return {
        "name": input_data.get("project_name") or Path(project_root).name,
        "root": project_root,
        "file_count": file_count,
        "languages": sorted(languages),
        "structure": structure,
    }


def _normalize_agent_input(task_id: str, input_data: Dict[str, Any], workspace: str) -> Dict[str, Any]:
    project_info = _collect_project_info(workspace, input_data)
    config = {
        "target_vulnerabilities": list(input_data.get("target_vulnerabilities") or []),
        "verification_level": input_data.get("verification_level") or "analysis_only",
        "exclude_patterns": list(input_data.get("exclude_patterns") or []),
        "target_files": list(input_data.get("target_files") or []),
        "max_iterations": int(input_data.get("max_iterations") or 50),
    }
    return {
        "project_info": project_info,
        "config": config,
        "project_root": workspace,
        "task_id": task_id,
    }


async def _initialize_tools(project_root: str, llm_service, input_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    from apps.deepaudit.agent_engine.tools import (
        BanditTool,
        CodeAnalysisTool,
        CommandInjectionTestTool,
        CreateVulnerabilityReportTool,
        DataFlowAnalysisTool,
        DeserializationTestTool,
        FileReadTool,
        FileSearchTool,
        GitleaksTool,
        ListFilesTool,
        NpmAuditTool,
        OSVScannerTool,
        PathTraversalTestTool,
        PatternMatchTool,
        ReflectTool,
        SafetyTool,
        SandboxManager,
        SemgrepTool,
        SqlInjectionTestTool,
        SstiTestTool,
        ThinkTool,
        VulnerabilityValidationTool,
        XssTestTool,
    )

    exclude_patterns = list(input_data.get("exclude_patterns") or [])
    target_files = list(input_data.get("target_files") or [])

    sandbox_manager = SandboxManager()
    await sandbox_manager.initialize()

    common_file_tools = {
        "read_file": FileReadTool(project_root, exclude_patterns=exclude_patterns, target_files=target_files),
        "search_files": FileSearchTool(project_root, exclude_patterns=exclude_patterns, target_files=target_files),
        "list_files": ListFilesTool(project_root, exclude_patterns=exclude_patterns, target_files=target_files),
        "pattern_match": PatternMatchTool(project_root),
        "think": ThinkTool(),
        "reflect": ReflectTool(),
    }

    report_tool = CreateVulnerabilityReportTool(project_root=project_root)

    analysis_tools = {
        **common_file_tools,
        "code_analysis": CodeAnalysisTool(llm_service),
        "dataflow_analysis": DataFlowAnalysisTool(llm_service),
        "semgrep": SemgrepTool(project_root, sandbox_manager=sandbox_manager),
        "bandit": BanditTool(project_root, sandbox_manager=sandbox_manager),
        "gitleaks": GitleaksTool(project_root, sandbox_manager=sandbox_manager),
        "npm_audit": NpmAuditTool(project_root, sandbox_manager=sandbox_manager),
        "safety": SafetyTool(project_root, sandbox_manager=sandbox_manager),
        "osv_scanner": OSVScannerTool(project_root, sandbox_manager=sandbox_manager),
        "create_vulnerability_report": report_tool,
    }

    verification_tools = {
        **common_file_tools,
        "vulnerability_validation": VulnerabilityValidationTool(llm_service),
        "command_injection_test": CommandInjectionTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "sql_injection_test": SqlInjectionTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "xss_test": XssTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "path_traversal_test": PathTraversalTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "ssti_test": SstiTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "deserialization_test": DeserializationTestTool(sandbox_manager=sandbox_manager, project_root=project_root),
        "create_vulnerability_report": report_tool,
    }

    recon_tools = dict(common_file_tools)
    orchestrator_tools = {
        "think": ThinkTool(),
        "reflect": ReflectTool(),
    }

    CreateVulnerabilityReportTool.clear_all_reports()

    return {
        "orchestrator": orchestrator_tools,
        "recon": recon_tools,
        "analysis": analysis_tools,
        "verification": verification_tools,
    }


def _normalize_finding_payload(item: Dict[str, Any]) -> Dict[str, Any] | None:
    title = str(item.get("title") or "").strip()
    file_path = str(item.get("file_path") or item.get("file") or "").strip()
    vulnerability_type = str(item.get("vulnerability_type") or item.get("type") or "other").strip().lower() or "other"
    severity = str(item.get("severity") or "low").strip().lower()
    if severity not in ALLOWED_SEVERITIES:
        severity = "low"
    if not title:
        return None

    line_start = item.get("line_start") or item.get("line") or item.get("line_number")
    line_end = item.get("line_end") or line_start
    recommendation = item.get("recommendation") or item.get("suggestion") or ""

    return {
        "vulnerability_type": vulnerability_type,
        "severity": severity,
        "title": title,
        "description": str(item.get("description") or "").strip() or None,
        "file_path": file_path or None,
        "line_start": int(line_start) if str(line_start or "").isdigit() else None,
        "line_end": int(line_end) if str(line_end or "").isdigit() else None,
        "code_snippet": str(item.get("code_snippet") or "").strip() or None,
        "is_verified": bool(item.get("is_verified")),
        "ai_confidence": float(item.get("confidence") or item.get("ai_confidence") or 0.8),
        "status": "open",
        "suggestion": str(recommendation).strip() or None,
        "poc": {
            "poc": item.get("poc"),
            "source": item.get("source"),
            "sink": item.get("sink"),
            "impact": item.get("impact"),
            "cwe_id": item.get("cwe_id"),
            "cvss_score": item.get("cvss_score"),
        },
    }


@sync_to_async
def _persist_findings(task_id: str, findings: list[Dict[str, Any]]) -> int:
    created = 0
    for item in findings:
        if not isinstance(item, dict):
            continue
        payload = _normalize_finding_payload(item)
        if not payload:
            continue
        AgentFinding.objects.create(task_id=task_id, **payload)
        created += 1
    return created


async def run_orchestrator_agent_async(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    异步运行 OrchestratorAgent。
    """
    event_manager = EventManager(task_id=task_id)
    await event_manager.init_sequence()
    event_emitter = AgentEventEmitter(task_id, event_manager)

    llm_service = _build_llm_service(input_data)
    normalized_input = _normalize_agent_input(task_id, input_data, workspace)
    tools = await _initialize_tools(workspace, llm_service, normalized_input["config"])

    recon_agent = ReconAgent(
        llm_service=llm_service,
        tools=tools.get("recon", {}),
        event_emitter=event_emitter,
    )
    analysis_agent = AnalysisAgent(
        llm_service=llm_service,
        tools=tools.get("analysis", {}),
        event_emitter=event_emitter,
    )
    verification_agent = VerificationAgent(
        llm_service=llm_service,
        tools=tools.get("verification", {}),
        event_emitter=event_emitter,
    )
    orchestrator = OrchestratorAgent(
        llm_service=llm_service,
        tools=tools.get("orchestrator", {}),
        event_emitter=event_emitter,
        sub_agents={
            "recon": recon_agent,
            "analysis": analysis_agent,
            "verification": verification_agent,
        },
    )

    try:
        await event_emitter.emit_phase_start("planning", "Starting Orchestrator Agent planning phase")
        result = await orchestrator.run(normalized_input)
        if result is None:
            raise RuntimeError("Orchestrator returned no result")
        if not result.success:
            raise RuntimeError(result.error or "Orchestrator returned unsuccessful result")

        result_data = result.data if isinstance(result.data, dict) else {}
        report_findings = []
        try:
            from apps.deepaudit.agent_engine.tools.reporting_tool import CreateVulnerabilityReportTool

            report_findings = CreateVulnerabilityReportTool.get_all_reports()
        except Exception:
            logger.debug("Failed to collect in-memory vulnerability reports", exc_info=True)

        findings = result_data.get("findings") if isinstance(result_data.get("findings"), list) else []
        if not findings and report_findings:
            findings = report_findings
            result_data["findings"] = findings

        if findings:
            persisted_count = await _persist_findings(task_id, findings)
            logger.info("Persisted %s findings for task %s", persisted_count, task_id)

        await event_emitter.emit_task_complete(
            findings_count=len(findings),
            duration_ms=result.duration_ms or 0,
            message="Orchestrator run completed.",
        )
    except Exception as e:
        logger.error(f"Agent Execution failed for task {task_id}: {e}", exc_info=True)
        await event_emitter.emit_task_error(str(e))
        raise


def run_orchestrator_agent_sync(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    由于 Celery worker 通常是同步运行，我们需要创建一个 event loop 来执行真正的 asyncio agent 逻辑。
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_orchestrator_agent_async(task_id, input_data, workspace))
    finally:
        loop.close()
