import asyncio
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict

from asgiref.sync import sync_to_async
from django.apps import apps

from apps.deepaudit.constants import (
    AGENT_PHASE_ANALYSIS,
    AGENT_PHASE_PLANNING,
    AGENT_PHASE_RECONNAISSANCE,
    AGENT_PHASE_REPORTING,
    AGENT_PHASE_VERIFICATION,
)
from apps.deepaudit.db_runtime import run_with_fresh_connection
from apps.deepaudit.agent_engine.agents import (
    AnalysisAgent,
    OrchestratorAgent,
    ReconAgent,
    VerificationAgent,
)
from apps.deepaudit.agent_engine.event_manager import AgentEventEmitter, EventManager
from apps.deepaudit.c_family import (
    C_FAMILY_TARGET_VULNERABILITIES,
    build_language_profile,
)
from apps.deepaudit.inventory_report import (
    extract_inventory_report,
    inventory_items_count,
    normalize_inventory_report,
)
from apps.deepaudit.scenario_profile import is_inventory_profile, resolve_scenario_profile
from apps.deepaudit.serialization import normalize_json_payload

if TYPE_CHECKING:
    from apps.deepaudit.agent_task.agent_task_model import AgentCheckpoint, AgentFinding

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
VULNERABILITY_TYPE_ALIASES = {
    "hardcoded_secrets": "hardcoded_secret",
    "hardcoded_credentials": "hardcoded_secret",
}


def _agent_finding_model():
    return apps.get_model("deepaudit", "AgentFinding")


def _agent_checkpoint_model():
    return apps.get_model("deepaudit", "AgentCheckpoint")


def _build_llm_service(input_data: Dict[str, Any]):
    if LLMService is None:
        return default_llm_service
    return LLMService(user_config=input_data)


def _normalize_target_file_path(path: Any) -> str:
    raw = str(path or "").strip().replace("\\", "/")
    if not raw:
        return ""
    normalized = os.path.normpath(raw).replace("\\", "/")
    if normalized in {"", "."}:
        return ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _effective_target_files_from_input(input_data: Dict[str, Any]) -> list[str]:
    agent_config = dict(input_data.get("agent_config") or {})
    selection_runtime = dict(agent_config.get("selection_runtime") or {})
    candidates = selection_runtime.get("resolved_target_files")
    if not isinstance(candidates, list):
        candidates = input_data.get("target_files") or []
    normalized_targets: list[str] = []
    seen: set[str] = set()
    for item in candidates:
        normalized = _normalize_target_file_path(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_targets.append(normalized)
    return normalized_targets


def _validate_runtime_target_files(project_root: str, target_files: list[str]) -> Dict[str, Any]:
    real_root = os.path.realpath(project_root)
    valid_files: list[str] = []
    missing_files: list[str] = []
    directory_targets: list[str] = []
    outside_targets: list[str] = []

    for item in target_files:
        normalized = _normalize_target_file_path(item)
        if not normalized:
            continue
        full_path = os.path.realpath(os.path.join(real_root, normalized))
        if os.path.commonpath([real_root, full_path]) != real_root:
            outside_targets.append(normalized)
            continue
        if not os.path.exists(full_path):
            missing_files.append(normalized)
            continue
        if not os.path.isfile(full_path):
            directory_targets.append(normalized)
            continue
        resolved_relative_path = os.path.relpath(full_path, real_root).replace("\\", "/")
        valid_files.append(resolved_relative_path)

    return {
        "valid_files": valid_files,
        "missing_files": missing_files,
        "directory_targets": directory_targets,
        "outside_targets": outside_targets,
    }


def _collect_project_info(project_root: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    target_files = _effective_target_files_from_input(input_data)
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
    target_files = _effective_target_files_from_input(input_data)
    language_profile = build_language_profile(
        [{"path": path} for path in (project_info.get("structure", {}).get("files") or [])],
        selected_file_paths=target_files,
    )
    agent_config = dict(input_data.get("agent_config") or {})
    audit_scope = dict(input_data.get("audit_scope") or {})
    requested_scenario_key = str(
        audit_scope.get("requested_scenario_key")
        or agent_config.get("requested_scenario_key")
        or audit_scope.get("scenario_key")
        or agent_config.get("scenario_key")
        or input_data.get("scenario_key")
        or ""
    ).strip() or None
    manual_target_vulnerabilities = list(
        agent_config.get("requested_target_vulnerabilities")
        or input_data.get("target_vulnerabilities")
        or []
    )
    scenario_profile = dict(
        agent_config.get("scenario_profile")
        or audit_scope.get("effective_profile")
        or {}
    )
    if (
        not scenario_profile
        or str(scenario_profile.get("selection_mode") or "").strip().lower() == "auto"
        or str(scenario_profile.get("scenario_key") or "").strip().lower() == "auto"
    ):
        scenario_profile = resolve_scenario_profile(
            requested_scenario_key,
            file_paths=target_files,
            manual_target_vulnerabilities=manual_target_vulnerabilities,
            language_profile=language_profile,
        )
    else:
        scenario_profile = normalize_json_payload(scenario_profile)

    scenario_key = str(scenario_profile.get("scenario_key") or "").strip().lower()
    target_vulnerabilities = list(
        scenario_profile.get("target_vulnerabilities")
        or input_data.get("target_vulnerabilities")
        or []
    )
    if not target_vulnerabilities and language_profile.get("is_c_family_dominant") and scenario_profile.get("legacy_c_family"):
        target_vulnerabilities = list(C_FAMILY_TARGET_VULNERABILITIES)

    if is_inventory_profile(scenario_profile):
        verification_level = "analysis_only"
    elif input_data.get("verification_level"):
        verification_level = input_data.get("verification_level")
    elif scenario_profile.get("legacy_c_family") or (
        language_profile.get("is_c_family_dominant")
        and scenario_key in {"concurrency", "api_chain", "critical_section"}
    ):
        verification_level = "sandbox"
    else:
        verification_level = "analysis_only"

    config = {
        "target_vulnerabilities": target_vulnerabilities,
        "verification_level": verification_level,
        "exclude_patterns": list(input_data.get("exclude_patterns") or []),
        "target_files": target_files,
        "max_iterations": int(input_data.get("max_iterations") or 50),
        "language_profile": language_profile,
        "scenario_profile": scenario_profile,
    }
    return {
        "project_info": {**project_info, "language_profile": language_profile},
        "config": config,
        "project_root": workspace,
        "task_id": task_id,
    }


async def _initialize_tools(
    project_root: str,
    llm_service,
    input_data: Dict[str, Any],
    *,
    enable_c_family_rag_fallback: bool = False,
    scenario_profile: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
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
        RunCodeTool,
        ExtractFunctionTool,
    )
    from apps.deepaudit.agent_engine.knowledge import (
        GetVulnerabilityKnowledgeTool,
        SecurityKnowledgeQueryTool,
    )
    from apps.deepaudit.rag import ProjectCodeRetriever

    exclude_patterns = list(input_data.get("exclude_patterns") or [])
    target_files = _effective_target_files_from_input(input_data)

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
    rag_query_tool = RAGQueryTool(
        project_retriever,
        search_tool=search_tool,
        enable_keyword_fallback=enable_c_family_rag_fallback,
    )
    security_code_search_tool = SecurityCodeSearchTool(project_retriever)
    function_context_tool = FunctionContextTool(
        project_retriever,
        search_tool=search_tool,
        enable_keyword_fallback=enable_c_family_rag_fallback,
    )
    run_code_tool = RunCodeTool(sandbox_manager=sandbox_manager, project_root=project_root)
    extract_function_tool = ExtractFunctionTool(project_root=project_root)
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
        "run_code": run_code_tool,
        "extract_function": extract_function_tool,
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

    tool_groups = {
        "orchestrator": orchestrator_tools,
        "recon": recon_tools,
        "analysis": analysis_tools,
        "verification": verification_tools,
    }
    return _filter_tool_groups_for_scenario(tool_groups, scenario_profile)


def _filter_tool_groups_for_scenario(
    tool_groups: Dict[str, Dict[str, Any]],
    scenario_profile: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    if not is_inventory_profile(scenario_profile):
        return tool_groups

    policy = dict((scenario_profile or {}).get("tool_policy") or {})
    allowed = {str(item).strip() for item in policy.get("allowed_tools") or [] if str(item).strip()}
    blocked = {str(item).strip() for item in policy.get("blocked_tools") or [] if str(item).strip()}
    filtered_groups: Dict[str, Dict[str, Any]] = {}
    for group_name, group_tools in tool_groups.items():
        filtered = dict(group_tools)
        if allowed:
            filtered = {name: tool for name, tool in filtered.items() if name in allowed}
        if blocked:
            filtered = {name: tool for name, tool in filtered.items() if name not in blocked}
        filtered_groups[group_name] = filtered
    return filtered_groups


def _normalize_finding_payload(item: Dict[str, Any]) -> Dict[str, Any] | None:
    def _text_or_none(value: Any) -> str | None:
        text = str(value or "").strip()
        return text or None

    def _json_dict(value: Any) -> Dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _first_text(*values: Any) -> str | None:
        for value in values:
            text = _text_or_none(value)
            if text:
                return text
        return None

    title = str(item.get("title") or "").strip()
    file_path = str(item.get("file_path") or item.get("file") or "").strip()
    vulnerability_type = str(item.get("vulnerability_type") or item.get("type") or "other").strip().lower() or "other"
    vulnerability_type = VULNERABILITY_TYPE_ALIASES.get(vulnerability_type, vulnerability_type)
    severity = str(item.get("severity") or "low").strip().lower()
    if severity not in ALLOWED_SEVERITIES:
        severity = "low"
    if not title:
        return None

    raw_poc = item.get("poc")
    poc_payload = _json_dict(raw_poc)
    validation_payload = _json_dict(
        item.get("validation") or item.get("verification") or poc_payload.get("validation")
    )
    line_start = item.get("line_start") or item.get("line") or item.get("line_number")
    line_end = item.get("line_end") or line_start
    matched_line = _first_text(
        item.get("matched_line"),
        poc_payload.get("matched_line"),
        validation_payload.get("matched_line"),
    )
    context = _first_text(
        item.get("context"),
        poc_payload.get("context"),
        validation_payload.get("context"),
    )
    evidence = _first_text(
        item.get("evidence"),
        validation_payload.get("evidence"),
        poc_payload.get("evidence"),
    )
    fix_code = _first_text(
        item.get("fix_code"),
        item.get("patched_code"),
        poc_payload.get("fix_code"),
        validation_payload.get("fix_code"),
    )
    ai_explanation = _first_text(
        item.get("ai_explanation"),
        item.get("detailed_analysis"),
        item.get("verification_details"),
        poc_payload.get("ai_explanation"),
        poc_payload.get("verification_details"),
        validation_payload.get("detailed_analysis"),
        validation_payload.get("details"),
    )
    recommendation = _first_text(
        item.get("recommendation"),
        item.get("suggestion"),
        validation_payload.get("recommendation"),
        poc_payload.get("recommendation"),
    )
    verdict = str(
        item.get("verdict")
        or validation_payload.get("verdict")
        or poc_payload.get("verdict")
        or item.get("status")
        or ""
    ).strip().lower()
    status = "open"
    if verdict == "false_positive":
        status = "false_positive"
    elif verdict in {"fixed", "wont_fix"}:
        status = verdict

    try:
        confidence = float(item.get("confidence") or item.get("ai_confidence") or 0.8)
    except (TypeError, ValueError):
        confidence = 0.8

    code_snippet = _first_text(
        item.get("code_snippet"),
        context,
        matched_line,
    )
    description = _first_text(
        item.get("description"),
        ai_explanation,
        evidence,
    )
    validation_is_vulnerable = validation_payload.get("is_vulnerable")
    is_verified = bool(
        item.get("is_verified")
        or item.get("verified")
        or validation_payload.get("is_verified")
    )
    if not is_verified and verdict in {"confirmed", "fixed", "wont_fix"}:
        is_verified = True
    if not is_verified and verdict == "likely" and confidence >= 0.8:
        is_verified = True
    if not is_verified and validation_is_vulnerable is True:
        is_verified = True

    verification_method = _first_text(
        item.get("verification_method"),
        validation_payload.get("verification_method"),
        validation_payload.get("method"),
        poc_payload.get("verification_method"),
    )
    verification_details = _first_text(
        item.get("verification_details"),
        validation_payload.get("details"),
        validation_payload.get("detailed_analysis"),
        evidence,
        poc_payload.get("verification_details"),
    )

    return {
        "vulnerability_type": vulnerability_type,
        "severity": severity,
        "title": title,
        "description": description,
        "file_path": file_path or None,
        "line_start": int(line_start) if str(line_start or "").isdigit() else None,
        "line_end": int(line_end) if str(line_end or "").isdigit() else None,
        "code_snippet": code_snippet,
        "is_verified": is_verified,
        "ai_confidence": confidence,
        "status": status,
        "suggestion": recommendation,
        "poc": {
            **poc_payload,
            "poc": poc_payload.get("poc", raw_poc if not isinstance(raw_poc, dict) else None),
            "source": item.get("source") or poc_payload.get("source"),
            "sink": item.get("sink") or poc_payload.get("sink"),
            "impact": item.get("impact") or poc_payload.get("impact"),
            "cwe_id": item.get("cwe_id") or poc_payload.get("cwe_id"),
            "cvss_score": item.get("cvss_score") or poc_payload.get("cvss_score"),
            "verdict": verdict or None,
            "verified_at": item.get("verified_at") or poc_payload.get("verified_at"),
            "matched_line": matched_line,
            "context": context,
            "evidence": evidence,
            "validation": validation_payload,
            "fix_code": fix_code,
            "ai_explanation": ai_explanation,
            "recommendation": recommendation,
            "verification_method": verification_method,
            "verification_details": verification_details,
        },
    }


@sync_to_async
def _persist_findings(task_id: str, findings: list[Dict[str, Any]]) -> int:
    def _persist() -> int:
        AgentFinding = _agent_finding_model()
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

    return run_with_fresh_connection(_persist)


@sync_to_async
def _initialize_task_runtime_state(task_id: str, total_files: int) -> None:
    from apps.deepaudit.agent_task.agent_task_model import AgentTask

    run_with_fresh_connection(
        AgentTask.objects.filter(id=task_id).update,
        total_files=total_files,
        current_phase=AGENT_PHASE_PLANNING,
        current_step="开始 planning 阶段",
    )


@sync_to_async
def _load_resume_checkpoint_context(resume_config: Dict[str, Any]) -> Dict[str, Any] | None:
    checkpoint_id = str(resume_config.get("resume_checkpoint_id") or "").strip()
    if not checkpoint_id:
        return None

    def _load() -> Dict[str, Any] | None:
        AgentCheckpoint = _agent_checkpoint_model()
        checkpoint = AgentCheckpoint.objects.filter(id=checkpoint_id, is_deleted=False).first()
        if not checkpoint:
            return None

        from apps.deepaudit.agent_engine.core.persistence import agent_persistence

        state_data = dict(checkpoint.state_data or {})
        if not agent_persistence.is_restorable_payload(state_data):
            return None

        return {
            "checkpoint_id": str(checkpoint.id),
            "agent_id": str(checkpoint.agent_id),
            "agent_type": str(checkpoint.agent_type or "").strip().lower() or "orchestrator",
            "checkpoint_name": checkpoint.checkpoint_name,
            "state_data": state_data,
        }

    return run_with_fresh_connection(_load)


def _phase_for_agent(agent_type: str) -> str | None:
    return {
        "recon": AGENT_PHASE_RECONNAISSANCE,
        "analysis": AGENT_PHASE_ANALYSIS,
        "verification": AGENT_PHASE_VERIFICATION,
        "orchestrator": AGENT_PHASE_PLANNING,
    }.get(str(agent_type or "").strip().lower())


def _build_resume_input(
    resume_context: Dict[str, Any],
    fallback_input: Dict[str, Any],
) -> Dict[str, Any]:
    runtime = dict((resume_context.get("state_data") or {}).get("runtime") or {})
    base_runtime = dict(runtime.get("base") or {})
    last_input = dict(base_runtime.get("last_input_data") or {})
    merged = {**last_input, **fallback_input}

    merged["project_info"] = {
        **dict(last_input.get("project_info") or {}),
        **dict(fallback_input.get("project_info") or {}),
    }
    merged["config"] = {
        **dict(last_input.get("config") or {}),
        **dict(fallback_input.get("config") or {}),
    }
    merged["project_root"] = fallback_input.get("project_root")
    merged["task_id"] = fallback_input.get("task_id")
    return merged


def _extract_result_findings(agent_type: str, result_data: Dict[str, Any]) -> list[Dict[str, Any]]:
    if str(agent_type or "").strip().lower() == "recon":
        findings = result_data.get("initial_findings") or result_data.get("findings") or []
    else:
        findings = result_data.get("findings") or []
    return [item for item in findings if isinstance(item, dict)]


async def run_orchestrator_agent_async(task_id: str, input_data: Dict[str, Any], workspace: str):
    """
    异步运行 OrchestratorAgent。
    """
    event_manager = EventManager(task_id=task_id)
    await event_manager.init_sequence()
    event_emitter = AgentEventEmitter(task_id, event_manager)

    runtime_target_files = _effective_target_files_from_input(input_data)
    if runtime_target_files:
        validation_result = _validate_runtime_target_files(workspace, runtime_target_files)
        valid_target_files = list(validation_result.get("valid_files") or [])
        directory_targets = list(validation_result.get("directory_targets") or [])
        missing_targets = list(validation_result.get("missing_files") or [])
        outside_targets = list(validation_result.get("outside_targets") or [])
        filtered_count = (
            len(directory_targets)
            + len(missing_targets)
            + len(outside_targets)
        )
        if filtered_count > 0:
            logger.warning(
                "DeepAudit Agent runner filtered invalid target scope before orchestrator start: task_id=%s valid_count=%s directory_count=%s missing_count=%s outside_count=%s directory_samples=%s missing_samples=%s outside_samples=%s",
                task_id,
                len(valid_target_files),
                len(directory_targets),
                len(missing_targets),
                len(outside_targets),
                directory_targets[:5],
                missing_targets[:5],
                outside_targets[:5],
            )
            await event_manager.emit(
                event_type="warning",
                phase=AGENT_PHASE_PLANNING,
                message="检测到目标范围中含目录或无效路径，已在启动前按真实文件范围纠偏",
                event_metadata={
                    "degraded_scope": True,
                    "valid_count": len(valid_target_files),
                    "directory_count": len(directory_targets),
                    "missing_count": len(missing_targets),
                    "outside_count": len(outside_targets),
                    "directory_samples": directory_targets[:10],
                    "missing_samples": missing_targets[:10],
                    "outside_samples": outside_targets[:10],
                    "resolved_samples": valid_target_files[:10],
                },
            )
        if not valid_target_files:
            message = "指定的目标目录或文件未解析为当前工作区中的有效文件，已中止 Agent 审计。"
            await event_manager.emit(
                event_type="task_error",
                phase=AGENT_PHASE_PLANNING,
                message=message,
                event_metadata={
                    "directory_count": len(directory_targets),
                    "missing_count": len(missing_targets),
                    "outside_count": len(outside_targets),
                },
            )
            raise RuntimeError(message)
        agent_config = dict(input_data.get("agent_config") or {})
        selection_runtime = dict(agent_config.get("selection_runtime") or {})
        selection_runtime.update(
            {
                "resolved_target_files": valid_target_files,
                "resolved_file_count": len(valid_target_files),
                "resolved_samples": valid_target_files[:10],
            }
        )
        input_data = {
            **input_data,
            "target_files": valid_target_files,
            "agent_config": {
                **agent_config,
                "selection_runtime": selection_runtime,
            },
        }

    llm_service = _build_llm_service(input_data)
    normalized_input = await sync_to_async(
        _normalize_agent_input,
        thread_sensitive=True,
    )(task_id, input_data, workspace)
    scenario_profile = dict(normalized_input.get("config", {}).get("scenario_profile") or {})
    knowledge_modules = list(scenario_profile.get("knowledge_modules") or [])
    await _initialize_task_runtime_state(
        task_id,
        int(normalized_input.get("project_info", {}).get("file_count") or 0),
    )
    tools = await _initialize_tools(
        workspace,
        llm_service,
        input_data,
        enable_c_family_rag_fallback=bool(scenario_profile.get("legacy_c_family")),
        scenario_profile=scenario_profile,
    )

    recon_agent = ReconAgent(
        llm_service=llm_service,
        tools=tools.get("recon", {}),
        event_emitter=event_emitter,
        knowledge_modules=knowledge_modules,
    )
    analysis_agent = AnalysisAgent(
        llm_service=llm_service,
        tools=tools.get("analysis", {}),
        event_emitter=event_emitter,
        knowledge_modules=knowledge_modules,
    )
    verification_agent = VerificationAgent(
        llm_service=llm_service,
        tools=tools.get("verification", {}),
        event_emitter=event_emitter,
        knowledge_modules=knowledge_modules,
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
        knowledge_modules=knowledge_modules,
    )
    agent_map = {
        "orchestrator": orchestrator,
        "recon": recon_agent,
        "analysis": analysis_agent,
        "verification": verification_agent,
    }

    try:
        resume_config = dict((input_data.get("agent_config") or {}).get("resume") or {})
        resume_context = await _load_resume_checkpoint_context(resume_config)
        resume_agent_type = str((resume_context or {}).get("agent_type") or "orchestrator").strip().lower() or "orchestrator"
        target_agent = agent_map.get(resume_agent_type, orchestrator)

        if resume_context:
            target_agent.restore_from_checkpoint_payload(dict(resume_context.get("state_data") or {}))
            resume_input = _build_resume_input(resume_context, normalized_input)
            resume_phase = _phase_for_agent(resume_agent_type)
            if resume_agent_type != "orchestrator" and resume_phase:
                await event_emitter.emit_phase_start(
                    resume_phase,
                    f"从检查点 {resume_context['checkpoint_id']} 恢复 {resume_agent_type} Agent",
                )
            else:
                await event_manager.emit(
                    event_type="info",
                    phase=resume_phase or AGENT_PHASE_PLANNING,
                    message=(
                        f"从检查点 {resume_context['checkpoint_id']} "
                        f"({resume_context.get('checkpoint_name') or resume_agent_type}) 恢复执行"
                    ),
                    event_metadata={
                        "resume": True,
                        "checkpoint_id": resume_context["checkpoint_id"],
                        "agent_id": resume_context["agent_id"],
                        "agent_type": resume_agent_type,
                    },
                )
            result = await target_agent.run(resume_input)
            if resume_agent_type != "orchestrator" and resume_phase:
                await event_emitter.emit_phase_complete(resume_phase, f"{resume_phase} 阶段完成")
        else:
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

        findings = _extract_result_findings(resume_agent_type, result_data)
        if not findings and report_findings:
            findings = report_findings
            result_data["findings"] = findings

        if is_inventory_profile(scenario_profile):
            raw_inventory_report = extract_inventory_report(result_data)
            inventory_report = normalize_inventory_report(
                raw_inventory_report,
                scenario_profile=scenario_profile,
                target_files=list(normalized_input.get("config", {}).get("target_files") or []),
                project_root=workspace,
            )
            from apps.deepaudit.agent_task.agent_task_services import update_task_inventory_report

            await sync_to_async(update_task_inventory_report)(
                task_id,
                inventory_report,
                inventory_items_count(inventory_report),
            )
            findings = []
            result_data["inventory_report"] = inventory_report
            await event_manager.emit(
                event_type="info",
                phase=AGENT_PHASE_REPORTING,
                message=f"Inventory 梳理报告已生成，条目数 {inventory_items_count(inventory_report)}",
                event_metadata={
                    "result_mode": "inventory",
                    "inventory_items_count": inventory_items_count(inventory_report),
                },
            )

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
