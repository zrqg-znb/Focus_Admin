import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict

from asgiref.sync import sync_to_async

from apps.deepaudit.agent_task.agent_task_model import AgentFinding
from apps.deepaudit.constants import AGENT_PHASE_PLANNING, AGENT_PHASE_REPORTING
from apps.deepaudit.agent_engine.agents import (
    AnalysisAgent,
    OrchestratorAgent,
    ReconAgent,
    VerificationAgent,
)
from apps.deepaudit.agent_engine.event_manager import AgentEventEmitter, EventManager

logger = logging.getLogger(__name__)

try:
    from apps.deepaudit.llm.service import (
        LLMService,
        llm_service as default_llm_service,
    )
except ImportError:
    LLMService = None

    class MockLLMService:
        pass

    default_llm_service = MockLLMService()
    logger.warning("Local LLMService not found, using mock for compilation check")
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


def _build_llm_service(input_data: Dict[str, Any]):
    if LLMService is None:
        return default_llm_service
    return LLMService(user_config=input_data)


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

    effective_file_count = len(target_files) if scope_limited else file_count

    return {
        "name": input_data.get("project_name") or Path(project_root).name,
        "root": project_root,
        "file_count": effective_file_count,
        "project_file_count": file_count,
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
        FunctionContextTool,
        KunlunMTool,
        ListFilesTool,
        NpmAuditTool,
        OSVScannerTool,
        PathTraversalTestTool,
        PatternMatchTool,
        QuickAuditTool,
        RAGQueryTool,
        ReflectTool,
        SafetyTool,
        SandboxManager,
        SecurityCodeSearchTool,
        SemgrepTool,
        SmartScanTool,
        SqlInjectionTestTool,
        SstiTestTool,
        ThinkTool,
        CppcheckTool,
        ClangTidyTool,
        ValgrindTool,
        VulnerabilityValidationTool,
        XssTestTool,
    )
    from apps.deepaudit.agent_engine.knowledge import (
        GetVulnerabilityKnowledgeTool,
        SecurityKnowledgeQueryTool,
    )
    from apps.deepaudit.rag import ProjectCodeRetriever

    exclude_patterns = list(input_data.get("exclude_patterns") or [])
    target_files = list(input_data.get("target_files") or [])

    sandbox_manager = SandboxManager()
    await sandbox_manager.initialize()

    project_retriever = ProjectCodeRetriever(
        project_root=project_root,
        user_config={
            "llm_config": dict(input_data.get("llm_config") or {}),
            "other_config": dict(input_data.get("other_config") or {}),
        },
        project_id=str(input_data.get("project_id") or "").strip() or None,
        project_name=str(input_data.get("project_name") or "").strip() or None,
        exclude_patterns=exclude_patterns,
        target_files=target_files,
    )

    read_file_tool = FileReadTool(
        project_root,
        exclude_patterns=exclude_patterns,
        target_files=target_files,
    )
    search_tool = FileSearchTool(
        project_root,
        exclude_patterns=exclude_patterns,
        target_files=target_files,
    )
    list_files_tool = ListFilesTool(
        project_root,
        exclude_patterns=exclude_patterns,
        target_files=target_files,
    )
    pattern_match_tool = PatternMatchTool(project_root)
    rag_query_tool = RAGQueryTool(project_retriever)
    security_code_search_tool = SecurityCodeSearchTool(project_retriever)
    function_context_tool = FunctionContextTool(project_retriever)
    security_knowledge_tool = SecurityKnowledgeQueryTool()
    vulnerability_knowledge_tool = GetVulnerabilityKnowledgeTool()

    common_file_tools = {
        "read_file": read_file_tool,
        "search_files": search_tool,
        "search_code": search_tool,
        "list_files": list_files_tool,
        "pattern_match": pattern_match_tool,
        "rag_query": rag_query_tool,
        "security_search": security_code_search_tool,
        "security_code_search": security_code_search_tool,
        "function_context": function_context_tool,
        "query_security_knowledge": security_knowledge_tool,
        "get_vulnerability_knowledge": vulnerability_knowledge_tool,
        "think": ThinkTool(),
        "reflect": ReflectTool(),
    }

    report_tool = CreateVulnerabilityReportTool(project_root=project_root)
    semgrep_tool = SemgrepTool(project_root, sandbox_manager=sandbox_manager)
    bandit_tool = BanditTool(project_root, sandbox_manager=sandbox_manager)
    gitleaks_tool = GitleaksTool(project_root, sandbox_manager=sandbox_manager)
    npm_audit_tool = NpmAuditTool(project_root, sandbox_manager=sandbox_manager)
    safety_tool = SafetyTool(project_root, sandbox_manager=sandbox_manager)
    osv_scanner_tool = OSVScannerTool(project_root, sandbox_manager=sandbox_manager)
    smart_scan_tool = SmartScanTool(project_root)
    quick_audit_tool = QuickAuditTool(project_root)
    kunlun_tool = KunlunMTool(project_root)
    cppcheck_tool = CppcheckTool(project_root, sandbox_manager=sandbox_manager)
    clang_tidy_tool = ClangTidyTool(project_root, sandbox_manager=sandbox_manager)
    valgrind_tool = ValgrindTool(project_root, sandbox_manager=sandbox_manager)

    analysis_tools = {
        **common_file_tools,
        "code_analysis": CodeAnalysisTool(llm_service),
        "dataflow_analysis": DataFlowAnalysisTool(llm_service),
        "semgrep": semgrep_tool,
        "semgrep_scan": semgrep_tool,
        "bandit": bandit_tool,
        "bandit_scan": bandit_tool,
        "gitleaks": gitleaks_tool,
        "gitleaks_scan": gitleaks_tool,
        "npm_audit": npm_audit_tool,
        "safety": safety_tool,
        "safety_scan": safety_tool,
        "osv_scanner": osv_scanner_tool,
        "osv_scan": osv_scanner_tool,
        "smart_scan": smart_scan_tool,
        "quick_audit": quick_audit_tool,
        "kunlun_scan": kunlun_tool,
        "cppcheck_scan": cppcheck_tool,
        "clang_tidy_scan": clang_tidy_tool,
        "valgrind_scan": valgrind_tool,
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

    recon_tools = {
        **common_file_tools,
        "semgrep_scan": semgrep_tool,
        "gitleaks_scan": gitleaks_tool,
        "smart_scan": smart_scan_tool,
        "cppcheck_scan": cppcheck_tool,
        "clang_tidy_scan": clang_tidy_tool,
        "valgrind_scan": valgrind_tool,
    }
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
    verdict = str(item.get("verdict") or item.get("status") or "").strip().lower()
    status = "open"
    if verdict == "false_positive":
        status = "false_positive"
    elif verdict in {"fixed", "wont_fix"}:
        status = verdict

    try:
        confidence = float(item.get("confidence") or item.get("ai_confidence") or 0.8)
    except (TypeError, ValueError):
        confidence = 0.8

    return {
        "vulnerability_type": vulnerability_type,
        "severity": severity,
        "title": title,
        "description": str(item.get("description") or "").strip() or None,
        "file_path": file_path or None,
        "line_start": int(line_start) if str(line_start or "").isdigit() else None,
        "line_end": int(line_end) if str(line_end or "").isdigit() else None,
        "code_snippet": str(item.get("code_snippet") or "").strip() or None,
        "is_verified": bool(item.get("is_verified")) or verdict in {"confirmed", "fixed", "wont_fix"},
        "ai_confidence": confidence,
        "status": status,
        "suggestion": str(recommendation).strip() or None,
        "poc": {
            "poc": item.get("poc"),
            "source": item.get("source"),
            "sink": item.get("sink"),
            "impact": item.get("impact"),
            "cwe_id": item.get("cwe_id"),
            "cvss_score": item.get("cvss_score"),
            "verdict": verdict or None,
            "verified_at": item.get("verified_at"),
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


@sync_to_async
def _initialize_task_runtime_state(task_id: str, total_files: int) -> None:
    from apps.deepaudit.agent_task.agent_task_model import AgentTask

    AgentTask.objects.filter(id=task_id).update(
        total_files=total_files,
        current_phase=AGENT_PHASE_PLANNING,
        current_step="开始 planning 阶段",
    )


async def run_orchestrator_agent_async(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    异步运行 OrchestratorAgent。
    """
    event_manager = EventManager(task_id=task_id)
    await event_manager.init_sequence()
    event_emitter = AgentEventEmitter(task_id, event_manager)

    llm_service = _build_llm_service(input_data)
    normalized_input = _normalize_agent_input(task_id, input_data, workspace)
    await _initialize_task_runtime_state(
        task_id,
        int(normalized_input.get("project_info", {}).get("file_count") or 0),
    )
    tools = await _initialize_tools(workspace, llm_service, input_data)

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
        await event_emitter.emit_phase_start(AGENT_PHASE_PLANNING, "Starting Orchestrator Agent planning phase")
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

        current_phase = event_emitter.current_phase
        if current_phase and current_phase != AGENT_PHASE_REPORTING:
            await event_emitter.emit_phase_complete(current_phase, f"{current_phase} 阶段完成")

        await event_emitter.emit_phase_start(AGENT_PHASE_REPORTING, "开始整理审计结果并生成报告")

        if findings:
            persisted_count = await _persist_findings(task_id, findings)
            logger.info("Persisted %s findings for task %s", persisted_count, task_id)

        from apps.deepaudit.agent_task.agent_task_services import refresh_task_snapshot

        await sync_to_async(refresh_task_snapshot)(task_id)
        await event_emitter.emit_phase_complete(AGENT_PHASE_REPORTING, "报告生成完成")
        await event_emitter.emit_task_complete(
            findings_count=len(findings),
            duration_ms=result.duration_ms or 0,
            message="Orchestrator run completed. 报告生成完成。",
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
