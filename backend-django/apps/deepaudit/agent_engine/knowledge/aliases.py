from __future__ import annotations

import re
from typing import Dict


_PREFIXES_TO_STRIP = ("vuln_", "framework_")


MODULE_ALIASES: Dict[str, str] = {
    # Common vulnerability aliases
    "sql": "vuln_sql_injection",
    "sqli": "vuln_sql_injection",
    "xss": "vuln_xss_reflected",
    "auth": "vuln_auth_bypass",
    "idor": "vuln_idor",
    "ssrf": "vuln_ssrf",
    "rce": "vuln_command_injection",
    "cmd": "vuln_command_injection",
    "command": "vuln_command_injection",
    "lfi": "vuln_path_traversal",
    "path": "vuln_path_traversal",
    "xxe": "vuln_xxe",
    "crypto": "vuln_weak_crypto",
    "weak_crypto": "vuln_weak_crypto",
    "hardcoded_secret": "vuln_hardcoded_secrets",
    "hardcoded_secrets": "vuln_hardcoded_secrets",
    "secret": "vuln_hardcoded_secrets",
    "password": "vuln_hardcoded_secrets",

    # Framework aliases
    "django": "framework_django",
    "fastapi": "framework_fastapi",
    "flask": "framework_flask",
    "express": "framework_express",
    "react": "framework_react",
    "supabase": "framework_supabase",

    # Automotive / embedded C knowledge
    "misra": "misra_c_baseline",
    "misra_c": "misra_c_baseline",
    "cert": "cert_c_baseline",
    "cert_c": "cert_c_baseline",
    "autosar": "autosar_c_baseline",
    "autosar_c": "autosar_c_baseline",
    "autosar_cpp": "autosar_cpp14_rules",
    "autosar_cpp14": "autosar_cpp14_rules",
    "cpp14": "autosar_cpp14_rules",
    "classic_platform": "autosar_classic_platform",
    "autosar_classic": "autosar_classic_platform",
    "rte": "autosar_classic_platform",
    "bsw": "autosar_bsw_contracts",
    "mcal": "autosar_bsw_contracts",
    "dcm": "autosar_bsw_contracts",
    "dem": "autosar_bsw_contracts",
    "nvm": "autosar_bsw_contracts",
    "com": "autosar_bsw_contracts",
    "pdur": "autosar_bsw_contracts",
    "autosar_os": "autosar_os_isr_task_contracts",
    "os_context": "autosar_os_isr_task_contracts",
    "ownership": "c_memory_ownership",
    "memory_ownership": "c_memory_ownership",
    "lifecycle": "c_memory_ownership",
    "memory": "c_memory_ownership",
    "interrupt": "c_interrupt_boundary",
    "interrupt_boundary": "c_interrupt_boundary",
    "critical_section": "c_interrupt_boundary",
    "criticalsection": "c_interrupt_boundary",
    "rtos": "c_interrupt_boundary",
    "isr": "c_interrupt_boundary",
    "irq": "c_interrupt_boundary",
    "task": "c_interrupt_boundary",
    "driver": "c_driver_init_sequence",
    "driver_init": "c_driver_init_sequence",
    "driver_init_sequence": "c_driver_init_sequence",
    "init": "c_driver_init_sequence",
    "startup": "c_driver_init_sequence",
    "hal": "c_driver_init_sequence",
    "bsp": "c_driver_init_sequence",
    "ring_buffer": "c_ring_buffer",
    "queue": "c_ring_buffer",
    "fifo": "c_ring_buffer",
    "dma": "c_dma_buffer_lifecycle",
    "dma_buffer_lifecycle": "c_dma_buffer_lifecycle",
    "descriptor": "c_dma_buffer_lifecycle",
    "mmio": "c_mmio_register_access",
    "mmio_register_access": "c_mmio_register_access",
    "register": "c_mmio_register_access",
    "register_access": "c_mmio_register_access",
    "hardware": "c_mmio_register_access",
    "contract": "c_api_contract_boundary",
    "api_contract_boundary": "c_api_contract_boundary",
    "api": "c_api_contract_boundary",
    "cleanup": "c_resource_cleanup_unwind",
    "resource_cleanup": "c_resource_cleanup_unwind",
    "resource_cleanup_unwind": "c_resource_cleanup_unwind",
    "unwind": "c_resource_cleanup_unwind",
    "safe_copy": "c_safe_copy_and_bounds",
    "safe_copy_and_bounds": "c_safe_copy_and_bounds",
    "bounds": "c_safe_copy_and_bounds",
    "copy": "c_safe_copy_and_bounds",
}


def normalize_module_name(module_name: str | None) -> str:
    """Normalize a knowledge module name to the canonical lookup form."""
    text = str(module_name or "").strip().lower()
    if not text:
        return ""
    text = re.sub(r"[\s\-/\\.:]+", "_", text)
    text = re.sub(r"[^a-z0-9_]+", "", text)
    text = re.sub(r"_+", "_", text).strip("_")
    for prefix in _PREFIXES_TO_STRIP:
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def resolve_module_alias(module_name: str | None) -> str:
    """Resolve a shorthand or friendly name to the canonical module id."""
    normalized = normalize_module_name(module_name)
    if not normalized:
        return ""
    return MODULE_ALIASES.get(normalized, normalized)
