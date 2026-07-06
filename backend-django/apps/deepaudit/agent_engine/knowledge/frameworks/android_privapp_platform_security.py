"""Android privileged app, platform permission and SELinux guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_PRIVAPP_PLATFORM_SECURITY = KnowledgeDocument(
    id="android_privapp_platform_security",
    title="Android 特权应用/平台权限/SELinux 边界",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "aosp",
        "privapp",
        "privileged",
        "platform_signature",
        "signature_permission",
        "selinux",
        "uid",
        "shareduserid",
        "system_app",
    ],
    severity="high",
    metadata={
        "sources": [
            "AndroidManifest uses-permission / permission / sharedUserId",
            "privapp-permissions XML",
            "SELinux allow/neverallow policy",
            "PackageManager/checkSignatures/checkPermission",
        ],
        "sinks": [
            "system/privileged permission guarded APIs",
            "device identifier, vehicle state, diagnostics or settings mutation",
            "system uid or platform signed service calls",
        ],
        "required_context": [
            "app install location and signing model",
            "permission protectionLevel",
            "privapp allowlist and SELinux domain",
            "caller uid/package and build variant",
        ],
        "false_positive_checks": [
            "permission is signature/system-only and caller cannot hold it",
            "privapp allowlist is absent for third-party package",
            "SELinux neverallow or domain transition blocks access",
            "code path is debug-only or product-feature disabled",
        ],
        "evidence_examples": [
            "Manifest permission declaration plus protectionLevel",
            "privapp-permissions allowlist line",
            "caller identity check before sensitive call",
            "SELinux policy or init service context",
        ],
        "severity_guidance": "提升为 high/critical 需要证明第三方或低权限进程可达系统/车辆/隐私敏感 sink；仅平台签名内部调用且 SELinux 阻断时降级。",
    },
    content="""
检查重点
- 区分普通应用、system app、priv-app、platform signed app、sharedUserId/system uid，不要把平台内部权限直接当作三方可利用入口。
- 审计 signature/signatureOrSystem/privileged 权限时，必须读取 Manifest、framework permission 定义、privapp-permissions allowlist 和调用方身份检查。
- SELinux domain、service_contexts、file_contexts、neverallow、init.rc 服务身份会改变可达性，是误报压制证据。
- checkCallingPermission、enforceCallingOrSelfPermission、PackageManager.checkSignatures、AppOps 检查点必须和敏感 sink 在同一调用路径内闭环。

证据要求
- finding 必须包含入口组件/IPC、调用方身份、权限保护级别、privapp/SELinux 配置证据、敏感 sink 和反例检查。
- 只有工具命中系统权限或 Manifest 权限名，缺少签名/allowlist/SELinux/调用路径证据时，verdict 应为 uncertain。
""".strip(),
)
