"""Android Binder system service deep security guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_BINDER_SYSTEM_SERVICE_SECURITY = KnowledgeDocument(
    id="android_binder_system_service_security",
    title="Android Binder/SystemService 深度身份边界",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "aosp",
        "binder",
        "aidl",
        "system_service",
        "car_service",
        "clearcallingidentity",
        "deathrecipient",
        "permission",
    ],
    severity="critical",
    metadata={
        "sources": [
            "AIDL Stub/onTransact/service method",
            "SystemService Binder registration",
            "Messenger/ResultReceiver callbacks",
            "PendingIntent callback entry",
        ],
        "sinks": [
            "vehicle control or diagnostic operations",
            "settings mutation",
            "file/device node access",
            "cross-user or privileged service call",
        ],
        "required_context": [
            "calling uid/package/userId",
            "permission/AppOps/signature check",
            "clearCallingIdentity lifetime",
            "callback registration and binder death cleanup",
        ],
        "false_positive_checks": [
            "enforceCallingPermission before every sensitive branch",
            "caller allowlist and user/profile check cover the sink",
            "clearCallingIdentity is scoped and restored in finally",
            "callback is same-process or system-only",
        ],
        "evidence_examples": [
            "AIDL method -> service implementation -> sink call chain",
            "Binder.getCallingUid plus package verification",
            "try/finally restoreCallingIdentity",
            "death recipient unregister path",
        ],
        "severity_guidance": "跨进程低权限调用可触达车辆、诊断、隐私或系统设置时为 critical/high；仅系统进程内部且权限闭环完整时降级。",
    },
    content="""
检查重点
- AIDL Stub、onTransact、SystemService public 方法、CarService/Vehicle service 方法都是权限边界，不是普通 Java 方法。
- clearCallingIdentity 会把执行身份切到 system_server/服务身份，必须检查调用前是否已完成权限、用户、包名、AppOps 和车辆状态校验。
- 回调、ResultReceiver、Messenger、DeathRecipient、linkToDeath/unlinkToDeath 需要检查生命周期和跨用户泄露。
- Parcelable/Bundle 参数必须检查类型、长度、范围、用户 ID、车辆状态和权限绑定，不能只看 NPE 或类型转换。

证据要求
- finding 需要入口 AIDL/Binder 方法、调用者身份来源、权限校验点、clearCallingIdentity 范围、敏感 sink 和反例检查。
- 缺少调用者身份或权限证据时，只能作为 candidate/uncertain，不应 confirmed。
""".strip(),
)
