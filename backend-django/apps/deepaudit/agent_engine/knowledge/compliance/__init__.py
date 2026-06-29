from .autosar_c_baseline import AUTOSAR_C_BASELINE
from .autosar_bsw_contracts import AUTOSAR_BSW_CONTRACTS
from .autosar_classic_platform import AUTOSAR_CLASSIC_PLATFORM
from .autosar_cpp14_rules import AUTOSAR_CPP14_RULES
from .autosar_os_isr_task_contracts import AUTOSAR_OS_ISR_TASK_CONTRACTS
from .cert_c_baseline import CERT_C_BASELINE
from .misra_c_baseline import MISRA_C_BASELINE

ALL_COMPLIANCE_DOCS = [
    MISRA_C_BASELINE,
    CERT_C_BASELINE,
    AUTOSAR_C_BASELINE,
    AUTOSAR_CPP14_RULES,
    AUTOSAR_CLASSIC_PLATFORM,
    AUTOSAR_BSW_CONTRACTS,
    AUTOSAR_OS_ISR_TASK_CONTRACTS,
]

__all__ = [
    'ALL_COMPLIANCE_DOCS',
    'AUTOSAR_C_BASELINE',
    'AUTOSAR_BSW_CONTRACTS',
    'AUTOSAR_CLASSIC_PLATFORM',
    'AUTOSAR_CPP14_RULES',
    'AUTOSAR_OS_ISR_TASK_CONTRACTS',
    'CERT_C_BASELINE',
    'MISRA_C_BASELINE',
]
