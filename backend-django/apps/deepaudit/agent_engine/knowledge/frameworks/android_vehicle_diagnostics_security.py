"""Automotive diagnostics, UDS, DoIP and bus gateway guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_VEHICLE_DIAGNOSTICS_SECURITY = KnowledgeDocument(
    id="android_vehicle_diagnostics_security",
    title="车载诊断/UDS/DoIP/CAN 网关安全",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "automotive",
        "vehicle",
        "diagnostics",
        "uds",
        "doip",
        "can",
        "lin",
        "dcm",
        "obd",
    ],
    severity="critical",
    metadata={
        "sources": [
            "diagnostic Activity/Service/Binder entry",
            "UDS/DoIP/CAN gateway Java wrapper",
            "vehicle HAL or native diagnostic bridge",
            "Bluetooth/Wi-Fi/USB diagnostic channel",
        ],
        "sinks": [
            "UDS session control/security access/routine control",
            "ECU reset/write data by identifier",
            "CAN/LIN frame injection",
            "diagnostic log or DTC clear operation",
        ],
        "required_context": [
            "caller permission and diagnostic role",
            "vehicle state constraints",
            "session/security access state machine",
            "transport exposure and feature flags",
        ],
        "false_positive_checks": [
            "diagnostic command is test-only and not in release build",
            "requires dealer mode, physical presence or secure session",
            "vehicle speed/gear/power state blocks the operation",
            "native/ECU layer enforces seed-key and allowlist",
        ],
        "evidence_examples": [
            "entry component -> diagnostic manager -> transport send chain",
            "UDS service ID or DID/routine evidence",
            "security access/session precondition",
            "vehicle state guard or missing guard",
        ],
        "severity_guidance": "能从应用/IPC/网络入口触达 ECU 控制、写入、复位、清 DTC 或 CAN 注入时 critical；只读且权限/状态闭环完整时降级。",
    },
    content="""
检查重点
- UDS/DoIP/CAN/LIN/OBD 相关代码必须按车辆安全边界审计，不按普通网络或普通 Java API 处理。
- 重点搜索 Diagnostic、DTC、DID、RoutineControl、SecurityAccess、SessionControl、DoIP、CAN frame、OBD、VehicleHal、CarService。
- 检查调用方权限、诊断角色、车辆速度/档位/电源状态、车型 feature flag、release/debug、seed-key/安全会话。
- JNI/native/MCU/ECU 层若二次校验，可作为反例；Java 层直接透传诊断命令到 native/transport 是高风险候选。

证据要求
- finding 必须绑定入口、诊断服务/命令、车辆状态约束、权限/身份、native/ECU 反例检查和影响点。
- 缺少车辆状态或诊断会话证据时降级为 uncertain。
""".strip(),
)
