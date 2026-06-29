"""AUTOSAR BSW service contract guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


AUTOSAR_BSW_CONTRACTS = KnowledgeDocument(
    id='autosar_bsw_contracts',
    title='AUTOSAR BSW/RTE/MCAL 接口契约',
    category=KnowledgeCategory.COMPLIANCE,
    tags=['autosar', 'bsw', 'rte', 'mcal', 'dem', 'dcm', 'nvm', 'com', 'pdur', 'det'],
    severity='medium',
    content="""
常见契约检查
- Rte_*、Com_*、PduR_*、Dcm_*、Dem_*、NvM_*、EcuM_*、SchM_*、Det_*、Mcu_*、Can_* 等调用必须确认返回值、模块初始化状态和可调用上下文。
- NvM/Flash/EEPROM 类持久化操作要确认异步完成、busy 状态、错误路径和掉电/重入约束。
- DCM/诊断路径要确认 DID/服务长度、会话/安全等级、负响应、缓冲区大小和 PDU 生命周期。
- COM/PduR/CanIf 路径要确认 PDU 长度、buffer ownership、Tx/Rx callback 上下文和 reentrancy。
- MCAL/MMIO 操作要确认寄存器访问顺序、volatile、临界区、屏障/延迟和硬件状态前置条件。

误报压制
- 如果调用点受生成配置、静态 PDU 长度、固定 DID 表或上游状态机严格约束，应把工具命中降级为 uncertain/false_positive，并记录反例证据。
""".strip(),
)
