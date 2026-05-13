from __future__ import annotations

from typing import Any, Iterable

from apps.deepaudit.audit_rule.audit_rule_model import AuditRuleSet
from apps.deepaudit.scenario.scenario_model import AuditScenarioProfile, ScenarioObjectiveType
from apps.deepaudit.c_family import (
    C_FAMILY_KNOWLEDGE_MODULES,
    C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME,
    C_FAMILY_SYSTEM_RULE_SET_NAME,
    C_FAMILY_TARGET_VULNERABILITIES,
    get_c_family_prompt_text,
    project_likely_c_family,
)
from apps.deepaudit.heuristics import DEFAULT_RULE_PATTERNS
from apps.deepaudit.prompt_template.prompt_template_model import PromptTemplate
from apps.deepaudit.serialization import normalize_json_payload

AUTO_SCENARIO_KEY = "auto"
GENERAL_SCENARIO_KEY = "general"
CONCURRENCY_SCENARIO_KEY = "concurrency"
API_CHAIN_SCENARIO_KEY = "api_chain"
CRITICAL_SECTION_SCENARIO_KEY = "critical_section"
LEGACY_C_FAMILY_SCENARIO_KEY = "legacy_c_family"

SUPPORTED_SCENARIO_KEYS = {
    AUTO_SCENARIO_KEY,
    GENERAL_SCENARIO_KEY,
    CONCURRENCY_SCENARIO_KEY,
    API_CHAIN_SCENARIO_KEY,
    CRITICAL_SECTION_SCENARIO_KEY,
    LEGACY_C_FAMILY_SCENARIO_KEY,
}

SYSTEM_SCENARIO_KEYS = {
    GENERAL_SCENARIO_KEY,
    CONCURRENCY_SCENARIO_KEY,
    API_CHAIN_SCENARIO_KEY,
}

SCENARIO_KEY_ALIASES = {
    "": AUTO_SCENARIO_KEY,
    "auto": AUTO_SCENARIO_KEY,
    "default": AUTO_SCENARIO_KEY,
    "general": GENERAL_SCENARIO_KEY,
    "d": GENERAL_SCENARIO_KEY,
    "scenario_d": GENERAL_SCENARIO_KEY,
    "concurrency": CONCURRENCY_SCENARIO_KEY,
    "race_condition": CONCURRENCY_SCENARIO_KEY,
    "a": CONCURRENCY_SCENARIO_KEY,
    "scenario_a": CONCURRENCY_SCENARIO_KEY,
    "api_chain": API_CHAIN_SCENARIO_KEY,
    "api": API_CHAIN_SCENARIO_KEY,
    "b": API_CHAIN_SCENARIO_KEY,
    "scenario_b": API_CHAIN_SCENARIO_KEY,
    "critical_section": CRITICAL_SECTION_SCENARIO_KEY,
    "critical-section": CRITICAL_SECTION_SCENARIO_KEY,
    "embedded": CRITICAL_SECTION_SCENARIO_KEY,
    "c": CRITICAL_SECTION_SCENARIO_KEY,
    "scenario_c": CRITICAL_SECTION_SCENARIO_KEY,
    "legacy_c_family": LEGACY_C_FAMILY_SCENARIO_KEY,
    "c_family": LEGACY_C_FAMILY_SCENARIO_KEY,
    "c-family": LEGACY_C_FAMILY_SCENARIO_KEY,
    "legacy": LEGACY_C_FAMILY_SCENARIO_KEY,
}

DEFAULT_GENERIC_TARGET_VULNERABILITIES = list(
    dict.fromkeys(pattern.issue_type for pattern in DEFAULT_RULE_PATTERNS)
)


def _unique_list(values: Iterable[str] | None) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in values or []:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _normalize_key(value: Any) -> str | None:
    text = str(value or "").strip().lower().replace(" ", "_")
    if not text:
        return None
    text = text.replace("-", "_")
    return SCENARIO_KEY_ALIASES.get(text, text)


def _rule_entry_from_pattern(pattern, *, custom_prompt: str | None = None) -> dict[str, Any]:
    return {
        "rule_code": pattern.code,
        "name": pattern.title,
        "description": pattern.description,
        "category": pattern.issue_type,
        "severity": pattern.severity,
        "fix_suggestion": pattern.suggestion,
        "custom_prompt": custom_prompt,
        "enabled": True,
    }


def _custom_rule_entry(
    *,
    rule_code: str,
    name: str,
    issue_type: str,
    severity: str,
    description: str,
    fix_suggestion: str,
    custom_prompt: str,
) -> dict[str, Any]:
    return {
        "rule_code": rule_code,
        "name": name,
        "description": description,
        "category": issue_type,
        "severity": severity,
        "fix_suggestion": fix_suggestion,
        "custom_prompt": custom_prompt,
        "enabled": True,
    }


def _build_rule_entries(
    issue_types: Iterable[str],
    *,
    custom_prompt: str,
    extra_rules: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()

    for issue_type in issue_types:
        pattern = next((item for item in DEFAULT_RULE_PATTERNS if item.issue_type == issue_type), None)
        if not pattern or pattern.issue_type in seen:
            continue
        entries.append(_rule_entry_from_pattern(pattern, custom_prompt=custom_prompt))
        seen.add(pattern.issue_type)

    for rule in extra_rules or []:
        issue_type = str(rule.get("category") or "").strip()
        rule_code = str(rule.get("rule_code") or "").strip()
        if (issue_type and issue_type in seen) or (rule_code and rule_code in seen):
            continue
        entries.append({**rule, "custom_prompt": rule.get("custom_prompt") or custom_prompt, "enabled": True})
        if issue_type:
            seen.add(issue_type)
        if rule_code:
            seen.add(rule_code)

    return entries


GENERAL_RULE_SET_RULES = _build_rule_entries(
    DEFAULT_GENERIC_TARGET_VULNERABILITIES,
    custom_prompt="请以通用安全审计视角分析该规则对应的风险，结合上下文判断是否为真实问题，并给出可执行修复建议。",
)

CONCURRENCY_RULE_SET_RULES = _build_rule_entries(
    ["race_condition", "deadlock", "embedded_concurrency"],
    custom_prompt=(
        "请优先定位共享状态、锁顺序、信号量、条件变量、ISR/任务上下文和临界区范围，"
        "梳理这些并发资源在代码中的出现位置、调用链和边界，不要只停留在漏洞定性。"
    ),
)

API_CHAIN_RULE_SET_RULES = _build_rule_entries(
    ["buffer_overflow", "use_after_free", "resource_leak", "format_string"],
    custom_prompt=(
        "请围绕高危 API 调用链梳理代码位置：从来源、长度控制、生命周期、所有权到危险 sink，"
        "输出关键文件、入口点、调用链和资源边界，而不是只做漏洞定性。"
    ),
)

CRITICAL_SECTION_RULE_SET_RULES = _build_rule_entries(
    ["deadlock", "api_contract_violation", "embedded_concurrency", "hardware_access"],
    custom_prompt=(
        "请聚焦临界区、ISR、DMA、寄存器访问和驱动/HAL 契约，检查返回值、上下文约束、"
        "阻塞调用和共享资源访问是否违背约定。"
    ),
)

LEGACY_C_FAMILY_RULE_SET_RULES = _build_rule_entries(
    [
        "buffer_overflow",
        "out_of_bounds",
        "integer_overflow",
        "null_dereference",
        "use_after_free",
        "double_free",
        "uninitialized_memory",
        "resource_leak",
        "race_condition",
        "deadlock",
        "embedded_concurrency",
        "hardware_access",
        "format_string",
        "api_contract_violation",
    ],
    custom_prompt=(
        "请结合上下文确认根因、触发条件、影响场景、边界/生命周期约束，并给出 CERT/CWE 语义级修复建议。"
    ),
)

SCENARIO_PROMPT_TEMPLATE_SEEDS = [
    {
        "name": "场景 A - 并发资源代码梳理",
        "description": "聚焦并发资源、锁、信号量、临界区与共享状态的代码梳理预设。",
        "template_type": "system",
        "content_zh": (
            "请围绕并发资源相关代码进行梳理：重点关注 pthread_*/mutex/sem/atomic/volatile/"
            "critical 区域、ISR 与任务共享状态、DMA 缓冲和寄存器镜像。输出时优先给出相关文件、"
            "调用链、资源边界和共享状态位置，而不是只做漏洞定性。"
        ),
        "content_en": (
            "Focus on concurrency-related code inventory: pthread_*/mutex/sem/atomic/volatile/critical "
            "areas, ISR/task shared state, DMA buffers and register mirrors. Prefer related files, call chains, "
            "resource boundaries and shared-state locations instead of only classifying vulnerabilities."
        ),
        "variables": {"language": "编程语言", "code": "代码内容"},
        "is_default": False,
        "is_system": True,
        "is_active": True,
    },
    {
        "name": "场景 B - 高危 API 调用链梳理",
        "description": "聚焦高危 API、生命周期和调用链位置的代码梳理预设。",
        "template_type": "system",
        "content_zh": (
            "请围绕 strcpy / strcat / sprintf / vsprintf / gets / scanf / memcpy / memmove / malloc / "
            "free / new / delete / printf / fprintf / syslog 等高危 API 调用链进行梳理，重点输出 "
            "来源、长度控制、所有权、释放路径和受影响文件，而不是只做漏洞判定。"
        ),
        "content_en": (
            "Trace high-risk API call chains around strcpy / strcat / sprintf / vsprintf / gets / scanf / "
            "memcpy / memmove / malloc / free / new / delete / printf / fprintf / syslog. Focus on sources, "
            "bounds, ownership, release paths and impacted files rather than only vulnerability classification."
        ),
        "variables": {"language": "编程语言", "code": "代码内容"},
        "is_default": False,
        "is_system": True,
        "is_active": True,
    },
    {
        "name": "场景 C - 临界区与硬件访问检查",
        "description": "聚焦 ISR、DMA、寄存器访问、临界区和接口契约的系统预设。",
        "template_type": "system",
        "content_zh": (
            "请重点检查 ISR、IRQ、DMA、寄存器访问、MMIO、volatile、内存屏障、临界区边界和 "
            "驱动/HAL API 契约。优先确认中断上下文是否调用了阻塞 API，是否存在共享寄存器或 "
            "DMA 描述符的并发写入，以及返回值和前置条件是否被严格遵守。"
        ),
        "content_en": (
            "Focus on ISR, IRQ, DMA, register access, MMIO, volatile, memory barriers, critical-section "
            "boundaries and driver/HAL API contracts. Verify that interrupt context never calls blocking APIs, "
            "shared registers or DMA descriptors are not written concurrently, and preconditions/return values "
            "are respected."
        ),
        "variables": {"language": "编程语言", "code": "代码内容"},
        "is_default": False,
        "is_system": True,
        "is_active": True,
    },
]

SCENARIO_RULE_SET_SEEDS = [
    {
        "name": "场景 A - 并发资源访问规则集",
        "description": "聚焦并发共享状态、锁顺序、信号量和临界区代码位置的系统规则集。",
        "language": "cpp",
        "rule_type": "builtin",
        "severity_weights": {"critical": 18, "high": 12, "medium": 6, "low": 2},
        "is_default": False,
        "is_system": True,
        "is_active": True,
        "rules": CONCURRENCY_RULE_SET_RULES,
    },
    {
        "name": "场景 B - 高危 API 调用链规则集",
        "description": "聚焦高危 API 调用链、内存生命周期和格式化字符串位置的系统规则集。",
        "language": "cpp",
        "rule_type": "builtin",
        "severity_weights": {"critical": 18, "high": 12, "medium": 6, "low": 2},
        "is_default": False,
        "is_system": True,
        "is_active": True,
        "rules": API_CHAIN_RULE_SET_RULES,
    },
    {
        "name": "场景 C - 临界区与硬件访问规则集",
        "description": "聚焦 ISR、DMA、寄存器访问和 API 契约的系统规则集。",
        "language": "cpp",
        "rule_type": "builtin",
        "severity_weights": {"critical": 20, "high": 14, "medium": 6, "low": 2},
        "is_default": False,
        "is_system": True,
        "is_active": True,
        "rules": CRITICAL_SECTION_RULE_SET_RULES,
    },
]


SCENARIO_DEFINITIONS: dict[str, dict[str, Any]] = {
    GENERAL_SCENARIO_KEY: {
        "scenario_code": "D",
        "scenario_name": "默认通用审计",
        "description": "默认通用审计，不注入场景特化知识或规则。",
        "objective_type": ScenarioObjectiveType.AUDIT,
        "prompt_template_name": "默认代码审计",
        "rule_set_name": "内置安全规则集",
        "knowledge_modules": [],
        "target_vulnerabilities": list(DEFAULT_GENERIC_TARGET_VULNERABILITIES),
        "focus_keywords": ["input", "request", "query", "auth", "secret", "file", "path", "url"],
        "selection_mode": "explicit",
        "resolution_reason": "explicit_general",
    },
    CONCURRENCY_SCENARIO_KEY: {
        "scenario_code": "A",
        "scenario_name": "并发资源代码梳理",
        "description": "聚焦并发资源、锁、信号量、临界区与共享状态的代码梳理。",
        "objective_type": ScenarioObjectiveType.INVENTORY,
        "prompt_template_name": "场景 A - 并发资源代码梳理",
        "rule_set_name": "场景 A - 并发资源访问规则集",
        "knowledge_modules": ["race_condition", "deadlock", "embedded_concurrency"],
        "target_vulnerabilities": ["race_condition", "deadlock", "embedded_concurrency"],
        "focus_keywords": [
            "pthread_",
            "mutex",
            "sem_",
            "semaphore",
            "lock",
            "critical",
            "atomic",
            "volatile",
            "ISR",
            "IRQ",
            "DMA",
            "taskENTER_CRITICAL",
            "taskEXIT_CRITICAL",
        ],
        "selection_mode": "explicit",
        "resolution_reason": "explicit_concurrency",
    },
    API_CHAIN_SCENARIO_KEY: {
        "scenario_code": "B",
        "scenario_name": "高危 API 调用链梳理",
        "description": "聚焦高危 API 调用链、生命周期和边界位置的代码梳理。",
        "objective_type": ScenarioObjectiveType.INVENTORY,
        "prompt_template_name": "场景 B - 高危 API 调用链梳理",
        "rule_set_name": "场景 B - 高危 API 调用链规则集",
        "knowledge_modules": ["buffer_overflow", "use_after_free", "resource_leak", "format_string"],
        "target_vulnerabilities": ["buffer_overflow", "use_after_free", "resource_leak", "format_string"],
        "focus_keywords": [
            "strcpy",
            "strcat",
            "sprintf",
            "vsprintf",
            "gets",
            "scanf",
            "memcpy",
            "memmove",
            "malloc",
            "calloc",
            "realloc",
            "free",
            "new",
            "delete",
            "printf",
            "fprintf",
            "syslog",
            "snprintf",
            "strncpy",
            "strlcpy",
        ],
        "selection_mode": "explicit",
        "resolution_reason": "explicit_api_chain",
    },
    CRITICAL_SECTION_SCENARIO_KEY: {
        "scenario_code": "C",
        "scenario_name": "临界区与硬件访问检查",
        "description": "聚焦 ISR、DMA、寄存器访问、临界区和接口契约。",
        "objective_type": ScenarioObjectiveType.INVENTORY,
        "prompt_template_name": "场景 C - 临界区与硬件访问检查",
        "rule_set_name": "场景 C - 临界区与硬件访问规则集",
        "knowledge_modules": ["embedded_concurrency", "deadlock", "api_contract_violation", "hardware_access"],
        "target_vulnerabilities": ["embedded_concurrency", "deadlock", "api_contract_violation"],
        "focus_keywords": [
            "ISR",
            "IRQ",
            "DMA",
            "register",
            "MMIO",
            "readl",
            "writel",
            "ioread",
            "iowrite",
            "volatile",
            "taskENTER_CRITICAL",
            "taskEXIT_CRITICAL",
            "disable_irq",
            "enable_irq",
        ],
        "selection_mode": "explicit",
        "resolution_reason": "explicit_critical_section",
    },
    LEGACY_C_FAMILY_SCENARIO_KEY: {
        "scenario_code": "LEGACY-C",
        "scenario_name": "嵌入式 C/C++ 深度审计",
        "description": "保留现有的 C/C++ 自动预设行为，兼容旧任务。",
        "objective_type": ScenarioObjectiveType.AUDIT,
        "prompt_template_name": C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME,
        "rule_set_name": C_FAMILY_SYSTEM_RULE_SET_NAME,
        "knowledge_modules": list(C_FAMILY_KNOWLEDGE_MODULES),
        "target_vulnerabilities": list(C_FAMILY_TARGET_VULNERABILITIES),
        "focus_keywords": [
            "pthread_",
            "mutex",
            "semaphore",
            "ISR",
            "IRQ",
            "DMA",
            "buffer",
            "memory",
            "lock",
            "volatile",
            "atomic",
        ],
        "selection_mode": "auto",
        "resolution_reason": "legacy_c_family_auto",
    },
}


def _prompt_template_seed_for(key: str) -> dict[str, Any]:
    if key == GENERAL_SCENARIO_KEY:
        return {
            "name": "默认代码审计",
            "description": "全量安全与质量扫描提示词模板",
            "template_type": "system",
            "content_zh": "你是 Focus DeepAudit 的安全审计助手，请关注高危漏洞、代码质量、可维护性和修复建议。",
            "content_en": "You are the Focus DeepAudit auditing assistant. Focus on security issues, quality risks, maintainability and remediation.",
            "variables": {"language": "编程语言", "code": "代码内容"},
            "is_default": True,
            "is_system": True,
            "is_active": True,
        }
    if key == LEGACY_C_FAMILY_SCENARIO_KEY:
        return {
            "name": C_FAMILY_SYSTEM_PROMPT_TEMPLATE_NAME,
            "description": "面向汽车级 MCU 嵌入式 C/C++ 项目的语义级深度审计模板",
            "template_type": "system",
            "content_zh": get_c_family_prompt_text(),
            "content_en": (
                "Audit the current C/C++ code unit as an embedded automotive MCU security reviewer. "
                "Focus on buffer overflows, out-of-bounds access, integer overflow or truncation, null dereference, "
                "use-after-free, double free, uninitialized memory, resource leaks, deadlocks, race conditions, "
                "ISR or task-context shared state, unsafe standard-library APIs, unchecked return values, and API contract violations."
            ),
            "variables": {"language": "编程语言", "code": "代码内容"},
            "is_default": False,
            "is_system": True,
            "is_active": True,
        }
    for item in SCENARIO_PROMPT_TEMPLATE_SEEDS:
        if item["name"] == SCENARIO_DEFINITIONS[key]["prompt_template_name"]:
            return item
    raise KeyError(key)


def _rule_set_seed_for(key: str) -> dict[str, Any]:
    if key == GENERAL_SCENARIO_KEY:
        return {
            "name": "内置安全规则集",
            "description": "基于 DeepAudit 迁移的默认安全启发式规则",
            "language": "all",
            "rule_type": "builtin",
            "severity_weights": {"critical": 10, "high": 5, "medium": 2, "low": 1},
            "is_default": True,
            "is_system": True,
            "is_active": True,
            "rules": GENERAL_RULE_SET_RULES,
        }
    if key == LEGACY_C_FAMILY_SCENARIO_KEY:
        return {
            "name": C_FAMILY_SYSTEM_RULE_SET_NAME,
            "description": "面向嵌入式 C/C++ 项目的 CERT/CWE 语义规则集",
            "language": "cpp",
            "rule_type": "builtin",
            "severity_weights": {"critical": 18, "high": 10, "medium": 5, "low": 2},
            "is_default": False,
            "is_system": True,
            "is_active": True,
            "rules": LEGACY_C_FAMILY_RULE_SET_RULES,
        }
    for item in SCENARIO_RULE_SET_SEEDS:
        if item["name"] == SCENARIO_DEFINITIONS[key]["rule_set_name"]:
            return item
    raise KeyError(key)


def _serialize_prompt_template(template: PromptTemplate | None, fallback_seed: dict[str, Any]) -> dict[str, Any]:
    if template:
        content_zh = str(template.content_zh or "").strip()
        content_en = str(template.content_en or "").strip()
        selected_content = content_zh or content_en
        return {
            "id": str(template.id),
            "name": template.name,
            "description": template.description or "",
            "template_type": template.template_type,
            "content_zh": content_zh,
            "content_en": content_en,
            "content": selected_content,
            "content_excerpt": selected_content[:320],
            "variables": normalize_json_payload(template.variables or {}),
            "is_default": template.is_default,
            "is_system": template.is_system,
            "is_active": template.is_active,
        }
    selected_content = str(fallback_seed.get("content_zh") or fallback_seed.get("content_en") or "").strip()
    return {
        "id": None,
        "name": fallback_seed.get("name"),
        "description": fallback_seed.get("description"),
        "template_type": fallback_seed.get("template_type") or "system",
        "content_zh": fallback_seed.get("content_zh") or "",
        "content_en": fallback_seed.get("content_en") or "",
        "content": selected_content,
        "content_excerpt": selected_content[:320],
        "variables": normalize_json_payload(fallback_seed.get("variables") or {}),
        "is_default": bool(fallback_seed.get("is_default", False)),
        "is_system": bool(fallback_seed.get("is_system", True)),
        "is_active": bool(fallback_seed.get("is_active", True)),
    }


def _serialize_rule_set(rule_set: AuditRuleSet | None, fallback_seed: dict[str, Any]) -> dict[str, Any]:
    if rule_set:
        rules_qs = rule_set.rules.filter(is_deleted=False, enabled=True).order_by("sort", "rule_code")
        rules = [
            {
                "rule_code": rule.rule_code,
                "name": rule.name,
                "description": rule.description,
                "category": rule.category,
                "severity": rule.severity,
                "custom_prompt": rule.custom_prompt,
                "fix_suggestion": rule.fix_suggestion,
                "enabled": rule.enabled,
            }
            for rule in rules_qs
        ]
        return {
            "id": str(rule_set.id),
            "name": rule_set.name,
            "description": rule_set.description or "",
            "language": rule_set.language,
            "rule_type": rule_set.rule_type,
            "severity_weights": normalize_json_payload(rule_set.severity_weights or {}),
            "is_default": rule_set.is_default,
            "is_system": rule_set.is_system,
            "is_active": rule_set.is_active,
            "rules_count": len(rules),
            "enabled_rules_count": len(rules),
            "rules": rules,
        }

    rules = [
        {
            "rule_code": rule["rule_code"],
            "name": rule["name"],
            "description": rule.get("description"),
            "category": rule["category"],
            "severity": rule["severity"],
            "custom_prompt": rule.get("custom_prompt"),
            "fix_suggestion": rule.get("fix_suggestion"),
            "enabled": rule.get("enabled", True),
        }
        for rule in fallback_seed.get("rules", [])
    ]
    return {
        "id": None,
        "name": fallback_seed.get("name"),
        "description": fallback_seed.get("description"),
        "language": fallback_seed.get("language") or "all",
        "rule_type": fallback_seed.get("rule_type") or "builtin",
        "severity_weights": normalize_json_payload(fallback_seed.get("severity_weights") or {}),
        "is_default": bool(fallback_seed.get("is_default", False)),
        "is_system": bool(fallback_seed.get("is_system", True)),
        "is_active": bool(fallback_seed.get("is_active", True)),
        "rules_count": len(rules),
        "enabled_rules_count": len(rules),
        "rules": rules,
    }


def _visible_prompt_template_queryset():
    return PromptTemplate.objects.filter(is_deleted=False, is_active=True, is_system=True)


def _visible_rule_set_queryset():
    return AuditRuleSet.objects.filter(is_deleted=False, is_active=True, is_system=True)


def _resolve_named_prompt_template(name: str) -> PromptTemplate | None:
    return _visible_prompt_template_queryset().filter(name=name).first()


def _resolve_named_rule_set(name: str) -> AuditRuleSet | None:
    return _visible_rule_set_queryset().filter(name=name).prefetch_related("rules").first()


def _build_tool_policy(
    *,
    focus_vulnerabilities: Iterable[str],
    search_keywords: Iterable[str],
    quick_mode: bool = False,
) -> dict[str, Any]:
    focus = _unique_list(focus_vulnerabilities)
    keywords = _unique_list(search_keywords)
    return {
        "semgrep_scan": {"rules": "auto"},
        "smart_scan": {
            "quick_mode": quick_mode,
            "focus_vulnerabilities": focus,
            "scan_types": ["pattern"],
        },
        "pattern_match": {"pattern_types": focus},
        "search_code": {"keywords": keywords},
        "first_pass_order": ["semgrep_scan", "smart_scan", "pattern_match"],
    }


def _build_agent_instructions(
    *,
    scenario_name: str,
    objective_type: str,
    target_vulnerabilities: Iterable[str],
    knowledge_modules: Iterable[str],
    search_keywords: Iterable[str],
) -> dict[str, dict[str, Any]]:
    targets = _unique_list(target_vulnerabilities)
    modules = _unique_list(knowledge_modules)
    keywords = _unique_list(search_keywords)

    if str(objective_type or "").strip().lower() == ScenarioObjectiveType.INVENTORY:
        return {
            "orchestrator": {
                "task": "先调度 recon 锁定相关文件与入口，再让 analysis 梳理调用链、资源边界和共享状态，最后让 verification/summary 归纳代码位置与影响范围。",
                "knowledge_modules": modules,
            },
            "recon": {
                "task": "优先定位与当前场景相关的模块、接口、资源访问点和关键文件，并输出可以继续深挖的代码位置。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "analysis": {
                "task": "梳理相关调用链、跨文件依赖、资源边界和上下文约束，输出具体代码位置与逻辑关系。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "verification": {
                "task": "补充确认边界、异常路径和上下文差异，整理为可直接交付的代码排查结论。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
        }

    if scenario_name == "并发资源访问排查":
        return {
            "orchestrator": {
                "task": "先调度 recon 找出并发共享状态、锁、信号量和 ISR/DMA 入口，再让 analysis 深挖锁顺序、竞争窗口和死锁风险，最后让 verification 验证触发条件。",
                "knowledge_modules": modules,
            },
            "recon": {
                "task": "优先定位 pthread_*/mutex/sem/atomic/volatile/ISR/DMA/共享状态相关代码，并输出高风险文件和入口点。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "analysis": {
                "task": "深入分析锁顺序、条件变量、信号量、临界区和共享状态访问，确认竞态或死锁是否真实存在。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "verification": {
                "task": "围绕并发窗口、锁等待、重入路径和共享资源生命周期，验证问题是否可触发并评估影响。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
        }

    if scenario_name == "高危 API 调用链梳理":
        return {
            "orchestrator": {
                "task": "先用 recon 定位高危 API 调用链，再让 analysis 追踪来源、长度控制和所有权，最后验证 UAF/泄漏/溢出影响。",
                "knowledge_modules": modules,
            },
            "recon": {
                "task": "优先定位 strcpy/strcat/sprintf/vsprintf/gets/scanf/memcpy/memmove/malloc/free/new/delete/printf/fprintf/syslog 等高危 API 的调用点。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "analysis": {
                "task": "深入梳理高危 API 的调用链、长度边界、生命周期和释放路径，确认缓冲区溢出、UAF 或资源泄漏是否成立。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "verification": {
                "task": "围绕输入长度、对象所有权、释放顺序和格式化字符串，验证漏洞是否能触发并给出最小复现路径。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
        }

    if scenario_name == "临界区与硬件访问检查":
        return {
            "orchestrator": {
                "task": "先调度 recon 找出 ISR、DMA、寄存器访问和临界区入口，再让 analysis 检查 API 契约与并发边界，最后让 verification 验证实际影响。",
                "knowledge_modules": modules,
            },
            "recon": {
                "task": "优先定位 ISR/IRQ/DMA/寄存器/MMIO/volatile/taskENTER_CRITICAL/taskEXIT_CRITICAL 等硬件与临界区相关代码。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "analysis": {
                "task": "深入分析 ISR、DMA、寄存器访问、内存屏障和驱动/HAL 契约，确认上下文约束和临界区边界是否被破坏。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
            "verification": {
                "task": "围绕中断上下文、DMA 描述符、寄存器访问顺序和返回值处理，验证硬件访问问题是否可复现。",
                "knowledge_modules": modules,
                "focus_keywords": keywords,
                "focus_vulnerabilities": targets,
            },
        }

    return {
        "orchestrator": {
            "task": "先调度 recon 做信息收集，再让 analysis 深入审计，必要时让 verification 验证发现，最后汇总结果。",
            "knowledge_modules": modules,
        },
        "recon": {
            "task": "识别项目结构、技术栈、入口点和高风险区域，尽量给出可直接深入分析的文件列表。",
            "knowledge_modules": modules,
            "focus_keywords": keywords,
            "focus_vulnerabilities": targets,
        },
        "analysis": {
            "task": "围绕目标漏洞类型进行深度审计，读取上下文并验证是否存在真实风险。",
            "knowledge_modules": modules,
            "focus_keywords": keywords,
            "focus_vulnerabilities": targets,
        },
        "verification": {
            "task": "针对已有候选问题进行验证，确认可利用性、触发条件与影响范围。",
            "knowledge_modules": modules,
            "focus_keywords": keywords,
            "focus_vulnerabilities": targets,
        },
    }


def _build_focus_summary(
    *,
    scenario_name: str,
    objective_type: str,
    target_vulnerabilities: Iterable[str],
    knowledge_modules: Iterable[str],
    search_keywords: Iterable[str],
) -> str:
    objective_label = "代码梳理" if str(objective_type or "").strip().lower() == ScenarioObjectiveType.INVENTORY else "漏洞审计"
    targets = ", ".join(_unique_list(target_vulnerabilities)) or "无特定目标"
    modules = ", ".join(_unique_list(knowledge_modules)) or "无特定知识模块"
    keywords = ", ".join(_unique_list(search_keywords)) or "无特定关键词"
    return (
        f"场景: {scenario_name}\n"
        f"- 输出目标: {objective_label}\n"
        f"- 目标漏洞: {targets}\n"
        f"- 知识模块: {modules}\n"
        f"- 搜索关键词: {keywords}"
    )


def _resolve_database_scenario_profile(scenario_key: str | None) -> AuditScenarioProfile | None:
    normalized_key = _normalize_key(scenario_key)
    if not normalized_key or normalized_key in {AUTO_SCENARIO_KEY}:
        return None
    try:
        return (
            AuditScenarioProfile.objects.filter(is_deleted=False, scenario_key=normalized_key)
            .select_related("prompt_template", "rule_set", "created_by")
            .first()
        )
    except Exception:
        return None


def _build_runtime_profile_from_record(
    scenario: AuditScenarioProfile,
    *,
    requested_scenario_key: str | None,
    project=None,
    file_paths: Iterable[str] | None = None,
    manual_target_vulnerabilities: Iterable[str] | None = None,
    language_profile: dict[str, Any] | None = None,
    selection_mode: str = "explicit",
    resolution_reason: str = "db_profile",
) -> dict[str, Any]:
    normalized_key = _normalize_key(scenario.scenario_key) or str(scenario.scenario_key or "").strip().lower() or GENERAL_SCENARIO_KEY
    definition_key = normalized_key if normalized_key in SCENARIO_DEFINITIONS else None
    definition = dict(SCENARIO_DEFINITIONS.get(definition_key, {}))
    objective_type = str(scenario.objective_type or definition.get("objective_type") or ScenarioObjectiveType.AUDIT).strip().lower()
    manual_targets = _unique_list(manual_target_vulnerabilities)
    language_profile = dict(language_profile or {})

    prompt_template = scenario.prompt_template
    rule_set = scenario.rule_set
    prompt_seed = _prompt_template_seed_for(definition_key or GENERAL_SCENARIO_KEY)
    rule_seed = _rule_set_seed_for(definition_key or GENERAL_SCENARIO_KEY)
    prompt_template_snapshot = _serialize_prompt_template(prompt_template, prompt_seed)
    rule_set_snapshot = _serialize_rule_set(rule_set, rule_seed)

    if rule_set:
        rule_categories = [
            str(rule.get("category") or "").strip()
            for rule in (rule_set_snapshot.get("rules") or [])
            if str(rule.get("category") or "").strip()
        ]
        rule_categories = _unique_list(rule_categories)
    else:
        rule_categories = []

    raw_tool_policy = normalize_json_payload(scenario.tool_policy or {})
    smart_scan_policy = dict(raw_tool_policy.get("smart_scan") or {})
    pattern_policy = dict(raw_tool_policy.get("pattern_match") or {})
    search_policy = dict(raw_tool_policy.get("search_code") or {})

    if manual_targets and definition_key == GENERAL_SCENARIO_KEY and not raw_tool_policy:
        target_vulnerabilities = manual_targets
        target_source = "manual"
    else:
        has_tool_targets = bool(
            smart_scan_policy.get("focus_vulnerabilities")
            or pattern_policy.get("pattern_types")
        )
        has_definition_targets = bool(definition.get("target_vulnerabilities"))
        target_vulnerabilities = _unique_list(
            smart_scan_policy.get("focus_vulnerabilities")
            or pattern_policy.get("pattern_types")
            or rule_categories
            or definition.get("target_vulnerabilities")
            or []
        )
        if has_tool_targets:
            target_source = "tool_policy"
        elif rule_categories:
            target_source = "rule_set"
        elif has_definition_targets:
            target_source = "scenario_definition"
        else:
            target_source = "empty"

    search_keywords = _unique_list(
        search_policy.get("keywords")
        or definition.get("focus_keywords")
        or []
    )

    tool_policy = normalize_json_payload(raw_tool_policy or {})
    if not tool_policy:
        tool_policy = _build_tool_policy(
            focus_vulnerabilities=target_vulnerabilities,
            search_keywords=search_keywords,
            quick_mode=False,
        )
    else:
        smart_scan = dict(tool_policy.get("smart_scan") or {})
        smart_scan.setdefault("quick_mode", False)
        smart_scan.setdefault("focus_vulnerabilities", target_vulnerabilities)
        smart_scan.setdefault("scan_types", ["pattern"])
        tool_policy["smart_scan"] = smart_scan
        pattern_match = dict(tool_policy.get("pattern_match") or {})
        pattern_match.setdefault("pattern_types", target_vulnerabilities)
        tool_policy["pattern_match"] = pattern_match
        search_code = dict(tool_policy.get("search_code") or {})
        search_code.setdefault("keywords", search_keywords)
        tool_policy["search_code"] = search_code
        tool_policy.setdefault("first_pass_order", ["semgrep_scan", "smart_scan", "pattern_match"])

    knowledge_modules = _unique_list(
        scenario.knowledge_modules or definition.get("knowledge_modules") or []
    )
    scenario_name = str(scenario.name or definition.get("scenario_name") or "场景").strip()
    scenario_code = (str(scenario.scenario_key or "").strip().upper() or definition.get("scenario_code") or "SCENARIO")[:24]

    if selection_mode == "auto" and manual_targets and not target_vulnerabilities:
        target_vulnerabilities = manual_targets
        target_source = "manual"

    agent_instructions = _build_agent_instructions(
        scenario_name=scenario_name,
        objective_type=objective_type,
        target_vulnerabilities=target_vulnerabilities,
        knowledge_modules=knowledge_modules,
        search_keywords=search_keywords,
    )
    focus_summary = _build_focus_summary(
        scenario_name=scenario_name,
        objective_type=objective_type,
        target_vulnerabilities=target_vulnerabilities,
        knowledge_modules=knowledge_modules,
        search_keywords=search_keywords,
    )

    resolved_scenario_key = normalized_key
    return {
        "scenario_key": normalized_key,
        "requested_scenario_key": requested_scenario_key,
        "resolved_scenario_key": resolved_scenario_key,
        "selection_mode": selection_mode,
        "resolution_reason": resolution_reason,
        "scenario_code": scenario_code,
        "scenario_name": scenario_name,
        "description": str(scenario.description or definition.get("description") or "").strip(),
        "objective_type": objective_type,
        "target_vulnerabilities": target_vulnerabilities,
        "target_vulnerability_source": target_source,
        "knowledge_modules": knowledge_modules,
        "focus_keywords": search_keywords,
        "prompt_template": prompt_template_snapshot,
        "rule_set": rule_set_snapshot,
        "tool_policy": tool_policy,
        "agent_instructions": agent_instructions,
        "focus_summary": focus_summary,
        "language_profile": normalize_json_payload(language_profile),
        "legacy_c_family": resolved_scenario_key == LEGACY_C_FAMILY_SCENARIO_KEY,
    }


def resolve_scenario_profile(
    scenario_key: str | None,
    *,
    project=None,
    file_paths: Iterable[str] | None = None,
    manual_target_vulnerabilities: Iterable[str] | None = None,
    language_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_key = _normalize_key(scenario_key)
    language_profile = dict(language_profile or {})
    project_is_c_family = bool(project and project_likely_c_family(project, file_paths=file_paths))
    has_c_family_language_profile = bool(language_profile.get("is_c_family_dominant"))
    c_family_context = project_is_c_family or has_c_family_language_profile
    manual_targets = _unique_list(manual_target_vulnerabilities)
    unknown_requested_key = normalized_key is not None and normalized_key not in SUPPORTED_SCENARIO_KEYS

    if normalized_key not in {AUTO_SCENARIO_KEY, None}:
        db_scenario = _resolve_database_scenario_profile(normalized_key)
        if db_scenario:
            return _build_runtime_profile_from_record(
                db_scenario,
                requested_scenario_key=normalized_key,
                project=project,
                file_paths=file_paths,
                manual_target_vulnerabilities=manual_target_vulnerabilities,
                language_profile=language_profile,
                selection_mode="explicit",
                resolution_reason="db_profile" if not db_scenario.is_system else "db_system_profile",
            )

    if normalized_key in SUPPORTED_SCENARIO_KEYS:
        profile_key = normalized_key
    elif normalized_key is None:
        profile_key = AUTO_SCENARIO_KEY
    else:
        profile_key = GENERAL_SCENARIO_KEY

    explicit_key = profile_key in SUPPORTED_SCENARIO_KEYS and profile_key != AUTO_SCENARIO_KEY
    definition_key = profile_key if explicit_key else GENERAL_SCENARIO_KEY
    definition = dict(SCENARIO_DEFINITIONS.get(definition_key, SCENARIO_DEFINITIONS[GENERAL_SCENARIO_KEY]))

    prompt_seed = _prompt_template_seed_for(definition_key)
    rule_seed = _rule_set_seed_for(definition_key)

    prompt_template = _resolve_named_prompt_template(str(definition.get("prompt_template_name") or prompt_seed["name"]))
    rule_set = _resolve_named_rule_set(str(definition.get("rule_set_name") or rule_seed["name"]))
    prompt_template_snapshot = _serialize_prompt_template(prompt_template, prompt_seed)
    rule_set_snapshot = _serialize_rule_set(rule_set, rule_seed)
    objective_type = str(definition.get("objective_type") or ScenarioObjectiveType.AUDIT).strip().lower()

    if profile_key == AUTO_SCENARIO_KEY:
        if manual_targets:
            target_vulnerabilities = manual_targets
            target_source = "manual"
        elif c_family_context:
            target_vulnerabilities = list(C_FAMILY_TARGET_VULNERABILITIES)
            target_source = "legacy_c_family"
        else:
            target_vulnerabilities = []
            target_source = "auto_default"
        knowledge_modules = list(C_FAMILY_KNOWLEDGE_MODULES) if c_family_context else []
        search_keywords = definition.get("focus_keywords") if c_family_context else []
        resolved_scenario_key = LEGACY_C_FAMILY_SCENARIO_KEY if c_family_context else GENERAL_SCENARIO_KEY
        scenario_name = "嵌入式 C/C++ 深度审计" if c_family_context else definition["scenario_name"]
        scenario_code = "LEGACY-C" if c_family_context else "AUTO"
        selection_mode = "auto"
        resolution_reason = definition.get("resolution_reason") if c_family_context else "auto_default"
    elif profile_key == GENERAL_SCENARIO_KEY:
        target_vulnerabilities = list(definition.get("target_vulnerabilities") or DEFAULT_GENERIC_TARGET_VULNERABILITIES)
        knowledge_modules = []
        search_keywords = definition.get("focus_keywords") or []
        resolved_scenario_key = GENERAL_SCENARIO_KEY
        scenario_name = definition["scenario_name"]
        scenario_code = definition["scenario_code"]
        target_source = "general"
        selection_mode = "explicit"
        resolution_reason = "unknown_scenario_fallback" if unknown_requested_key else (definition.get("resolution_reason") or "explicit_general")
        objective_type = str(definition.get("objective_type") or ScenarioObjectiveType.AUDIT)
    elif profile_key in {
        CONCURRENCY_SCENARIO_KEY,
        API_CHAIN_SCENARIO_KEY,
        CRITICAL_SECTION_SCENARIO_KEY,
        LEGACY_C_FAMILY_SCENARIO_KEY,
    }:
        target_vulnerabilities = list(definition.get("target_vulnerabilities") or [])
        knowledge_modules = list(definition.get("knowledge_modules") or [])
        search_keywords = definition.get("focus_keywords") or []
        resolved_scenario_key = profile_key
        scenario_name = definition["scenario_name"]
        scenario_code = definition["scenario_code"]
        target_source = "scenario"
        selection_mode = "explicit"
        resolution_reason = "unknown_scenario_fallback" if unknown_requested_key else (definition.get("resolution_reason") or f"explicit_{profile_key}")
        objective_type = str(definition.get("objective_type") or ScenarioObjectiveType.AUDIT)
    else:
        target_vulnerabilities = list(definition.get("target_vulnerabilities") or DEFAULT_GENERIC_TARGET_VULNERABILITIES)
        knowledge_modules = []
        search_keywords = definition.get("focus_keywords") or []
        resolved_scenario_key = GENERAL_SCENARIO_KEY
        scenario_name = definition["scenario_name"]
        scenario_code = definition["scenario_code"]
        target_source = "fallback"
        selection_mode = "explicit"
        resolution_reason = "unknown_scenario_fallback"
        objective_type = str(definition.get("objective_type") or ScenarioObjectiveType.AUDIT)

    if profile_key == AUTO_SCENARIO_KEY and not c_family_context:
        scenario_name = definition["scenario_name"]
        scenario_code = definition["scenario_code"]

    if profile_key == AUTO_SCENARIO_KEY and not c_family_context and manual_targets:
        target_vulnerabilities = manual_targets

    if profile_key == AUTO_SCENARIO_KEY and not c_family_context:
        target_source = "auto_default"

    tool_policy = _build_tool_policy(
        focus_vulnerabilities=target_vulnerabilities,
        search_keywords=search_keywords,
        quick_mode=False,
    )
    agent_instructions = _build_agent_instructions(
        scenario_name=scenario_name,
        objective_type=objective_type,
        target_vulnerabilities=target_vulnerabilities,
        knowledge_modules=knowledge_modules,
        search_keywords=search_keywords,
    )
    focus_summary = _build_focus_summary(
        scenario_name=scenario_name,
        objective_type=objective_type,
        target_vulnerabilities=target_vulnerabilities,
        knowledge_modules=knowledge_modules,
        search_keywords=search_keywords,
    )

    return {
        "scenario_key": profile_key,
        "requested_scenario_key": normalized_key,
        "resolved_scenario_key": resolved_scenario_key,
        "selection_mode": selection_mode,
        "resolution_reason": resolution_reason,
        "scenario_code": scenario_code,
        "scenario_name": scenario_name,
        "description": definition.get("description", ""),
        "objective_type": objective_type,
        "target_vulnerabilities": _unique_list(target_vulnerabilities),
        "target_vulnerability_source": target_source,
        "knowledge_modules": _unique_list(knowledge_modules),
        "focus_keywords": _unique_list(search_keywords),
        "prompt_template": prompt_template_snapshot,
        "rule_set": rule_set_snapshot,
        "tool_policy": tool_policy,
        "agent_instructions": agent_instructions,
        "focus_summary": focus_summary,
        "language_profile": normalize_json_payload(language_profile),
        "legacy_c_family": resolved_scenario_key == LEGACY_C_FAMILY_SCENARIO_KEY,
    }


def get_scenario_agent_instruction(
    profile: dict[str, Any] | None,
    agent_role: str,
) -> dict[str, Any]:
    scenario = dict(profile or {})
    instructions = dict((scenario.get("agent_instructions") or {}).get(agent_role) or {})
    return {
        "task": str(instructions.get("task") or "").strip(),
        "knowledge_modules": _unique_list(instructions.get("knowledge_modules") or scenario.get("knowledge_modules") or []),
        "focus_keywords": _unique_list(instructions.get("focus_keywords") or scenario.get("focus_keywords") or []),
        "focus_vulnerabilities": _unique_list(
            instructions.get("focus_vulnerabilities") or scenario.get("target_vulnerabilities") or []
        ),
    }


def build_scenario_prompt_block(profile: dict[str, Any] | None, agent_role: str) -> str:
    scenario = dict(profile or {})
    if not scenario:
        return ""

    prompt_template = dict(scenario.get("prompt_template") or {})
    rule_set = dict(scenario.get("rule_set") or {})
    tool_policy = dict(scenario.get("tool_policy") or {})
    instruction = get_scenario_agent_instruction(scenario, agent_role)
    prompt_content = str(prompt_template.get("content") or prompt_template.get("content_zh") or "").strip()
    rule_lines = []
    for rule in (rule_set.get("rules") or [])[:8]:
        rule_lines.append(
            f"- [{rule.get('severity', 'medium')}] {rule.get('rule_code', '')} / {rule.get('category', '')}: "
            f"{rule.get('name', '')}"
        )

    smart_scan_policy = dict(tool_policy.get("smart_scan") or {})
    pattern_policy = dict(tool_policy.get("pattern_match") or {})
    search_policy = dict(tool_policy.get("search_code") or {})

    lines = [
        "<scenario_profile>",
        f"场景键: {scenario.get('scenario_key')}",
        f"场景名称: {scenario.get('scenario_name')}",
        f"场景说明: {scenario.get('description')}",
        f"输出目标: {'代码梳理' if str(scenario.get('objective_type') or '').strip().lower() == ScenarioObjectiveType.INVENTORY else '漏洞审计'}",
        f"目标漏洞: {', '.join(_unique_list(scenario.get('target_vulnerabilities') or [])) or '无'}",
        f"知识模块: {', '.join(_unique_list(scenario.get('knowledge_modules') or [])) or '无'}",
        f"关键词: {', '.join(_unique_list(scenario.get('focus_keywords') or [])) or '无'}",
        f"提示词模板: {prompt_template.get('name') or '未知'}",
        f"规则集: {rule_set.get('name') or '未知'}",
    ]
    if prompt_content:
        lines.extend(["", "### 提示词模板内容", prompt_content])
    if rule_lines:
        lines.extend(["", "### 规则集重点", *rule_lines])

    lines.extend(
        [
            "",
            "### 工具策略",
            f"- semgrep_scan: rules={dict(tool_policy.get('semgrep_scan') or {}).get('rules', 'auto')}",
            f"- smart_scan: focus_vulnerabilities={', '.join(_unique_list(smart_scan_policy.get('focus_vulnerabilities') or [])) or '无'}",
            f"- pattern_match: pattern_types={', '.join(_unique_list(pattern_policy.get('pattern_types') or [])) or '无'}",
            f"- search_code: keywords={', '.join(_unique_list(search_policy.get('keywords') or [])) or '无'}",
            "",
            "### 当前 Agent 指令",
            f"- role: {agent_role}",
            f"- task: {instruction.get('task') or '无'}",
            f"- knowledge_modules: {', '.join(_unique_list(instruction.get('knowledge_modules') or [])) or '无'}",
            f"- focus_keywords: {', '.join(_unique_list(instruction.get('focus_keywords') or [])) or '无'}",
            f"- focus_vulnerabilities: {', '.join(_unique_list(instruction.get('focus_vulnerabilities') or [])) or '无'}",
            "</scenario_profile>",
        ]
    )
    return "\n".join(lines)


def build_scenario_task_block(profile: dict[str, Any] | None, agent_role: str) -> str:
    scenario = dict(profile or {})
    if not scenario:
        return ""
    instruction = get_scenario_agent_instruction(scenario, agent_role)
    tool_policy = dict(scenario.get("tool_policy") or {})
    smart_scan_policy = dict(tool_policy.get("smart_scan") or {})
    pattern_policy = dict(tool_policy.get("pattern_match") or {})
    search_policy = dict(tool_policy.get("search_code") or {})

    lines = [
        "## 场景预设",
        f"- 场景: {scenario.get('scenario_name')}",
        f"- 输出目标: {'代码梳理' if str(scenario.get('objective_type') or '').strip().lower() == ScenarioObjectiveType.INVENTORY else '漏洞审计'}",
        f"- 当前模式: {'自动' if scenario.get('selection_mode') == 'auto' else '显式'}",
        f"- 目标漏洞: {', '.join(_unique_list(scenario.get('target_vulnerabilities') or [])) or '无'}",
        f"- 知识模块: {', '.join(_unique_list(scenario.get('knowledge_modules') or [])) or '无'}",
        f"- 搜索关键词: {', '.join(_unique_list(scenario.get('focus_keywords') or [])) or '无'}",
        f"- smart_scan focus: {', '.join(_unique_list(smart_scan_policy.get('focus_vulnerabilities') or [])) or '无'}",
        f"- pattern_match types: {', '.join(_unique_list(pattern_policy.get('pattern_types') or [])) or '无'}",
        f"- search_code keywords: {', '.join(_unique_list(search_policy.get('keywords') or [])) or '无'}",
    ]

    if instruction.get("task"):
        lines.extend(["", "### 场景任务", instruction["task"]])

    return "\n".join(lines)
