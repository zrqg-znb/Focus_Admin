"""Android Intent, deep link and PendingIntent guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_INTENT_PENDINGINTENT_SECURITY = KnowledgeDocument(
    id="android_intent_pendingintent_security",
    title="Android Intent/DeepLink/PendingIntent 暴露链路",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "intent",
        "deeplink",
        "pendingintent",
        "task_hijacking",
        "broadcast",
        "uri",
        "parcelable",
    ],
    severity="high",
    metadata={
        "sources": [
            "Manifest intent-filter and exported components",
            "getIntent/onNewIntent/onReceive/onStartCommand",
            "PendingIntent factory calls",
            "URI/deep link handlers",
        ],
        "sinks": [
            "privileged Activity/Service action",
            "broadcast command handling",
            "file/content URI grant",
            "account, vehicle, navigation or diagnostics operation",
        ],
        "required_context": [
            "exported/permission and intent-filter data",
            "PendingIntent mutability and explicit package/component",
            "extra/Parcelable/URI validation",
            "task affinity and launch mode",
        ],
        "false_positive_checks": [
            "component exported=false or protected by signature permission",
            "PendingIntent is immutable and explicit",
            "deep link host/path is strict and parameters validated",
            "action is internal-only or guarded by package allowlist",
        ],
        "evidence_examples": [
            "Manifest data/action/category evidence",
            "entry method reads controllable extras",
            "FLAG_IMMUTABLE/FLAG_MUTABLE evidence",
            "sink reached after insufficient validation",
        ],
        "severity_guidance": "外部 Intent/PendingIntent 可控参数触达权限操作、隐私或车辆状态变更时 high；仅内部显式不可变 PendingIntent 时降级。",
    },
    content="""
检查重点
- exported + intent-filter、deep link、scheme/host/path、taskAffinity/launchMode 会决定外部可达性。
- PendingIntent 必须关注 FLAG_IMMUTABLE/FLAG_MUTABLE、显式 component/package、requestCode 唯一性和是否携带可被篡改 extra。
- getIntent、onNewIntent、onReceive、onStartCommand、Bundle/Parcelable/Uri 输入进入文件、WebView、诊断、HMI、账号或车辆状态 sink 时需要上下文验证。
- Broadcast 发送/接收应检查权限、显式包名、受控 action 和跨用户限制。

证据要求
- finding 需要 Manifest/入口方法、可控参数、PendingIntent/DeepLink 配置、sink 和反例检查。
- 只发现 getIntent 或 PendingIntent 字样不足以确认漏洞。
""".strip(),
)
