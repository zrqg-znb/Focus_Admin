from .autosar_c_baseline import AUTOSAR_C_BASELINE
from .cert_c_baseline import CERT_C_BASELINE
from .misra_c_baseline import MISRA_C_BASELINE

ALL_COMPLIANCE_DOCS = [
    MISRA_C_BASELINE,
    CERT_C_BASELINE,
    AUTOSAR_C_BASELINE,
]

__all__ = [
    'ALL_COMPLIANCE_DOCS',
    'AUTOSAR_C_BASELINE',
    'CERT_C_BASELINE',
    'MISRA_C_BASELINE',
]
