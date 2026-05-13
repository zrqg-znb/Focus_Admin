from .c_api_contract_boundary import C_API_CONTRACT_BOUNDARY
from .c_dma_buffer_lifecycle import C_DMA_BUFFER_LIFECYCLE
from .c_mmio_register_access import C_MMIO_REGISTER_ACCESS
from .c_ring_buffer import C_RING_BUFFER

ALL_CODE_PATTERN_DOCS = [
    C_RING_BUFFER,
    C_MMIO_REGISTER_ACCESS,
    C_DMA_BUFFER_LIFECYCLE,
    C_API_CONTRACT_BOUNDARY,
]

__all__ = [
    'ALL_CODE_PATTERN_DOCS',
    'C_API_CONTRACT_BOUNDARY',
    'C_DMA_BUFFER_LIFECYCLE',
    'C_MMIO_REGISTER_ACCESS',
    'C_RING_BUFFER',
]
