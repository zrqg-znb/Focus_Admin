"""Android automotive OTA/update package security guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_OTA_UPDATE_SECURITY = KnowledgeDocument(
    id="android_ota_update_security",
    title="Android/车机 OTA 升级与包完整性安全",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "ota",
        "update_engine",
        "package_installer",
        "signature",
        "rollback",
        "downgrade",
        "ab_update",
    ],
    severity="critical",
    metadata={
        "sources": [
            "download/update manager entry",
            "PackageInstaller/UpdateEngine API",
            "recovery or native update bridge",
            "USB/local package import",
        ],
        "sinks": [
            "install/update package",
            "payload apply",
            "rollback/downgrade",
            "firmware or map/resource package activation",
        ],
        "required_context": [
            "signature/hash verification",
            "transport TLS and pinning",
            "version/rollback policy",
            "storage path and file permission",
            "failure recovery and power state",
        ],
        "false_positive_checks": [
            "payload signature verified by update_engine/recovery",
            "download file is integrity checked before apply",
            "downgrade rejected by version/rollback index",
            "source is restricted to trusted system updater",
        ],
        "evidence_examples": [
            "URL/local path -> downloaded file -> verify -> applyPayload chain",
            "certificate/hash verification code",
            "rollback index or version check",
            "failure cleanup path",
        ],
        "severity_guidance": "可绕过签名/完整性或降级安装系统/固件包时 critical；仅资源包且服务端签名闭环完整时按影响降级。",
    },
    content="""
检查重点
- OTA、地图包、语音包、HMI 资源包、固件包都需要完整性、来源、版本、防回滚和失败恢复证据。
- 重点搜索 UpdateEngine.applyPayload、PackageInstaller、RecoverySystem、payload.bin、metadata、signature、rollback、download、USB/import。
- 文件下载到外部存储、可写目录或由 Intent/URI 指定路径时，必须检查 TOCTOU、权限、hash/signature 和 apply 前一致性。
- TLS、证书校验、明文配置和代理场景会影响 OTA 包来源可信度。

证据要求
- finding 需要入口、包来源、校验链、安装/apply sink、版本/回滚策略和反例检查。
- 只看到下载或安装 API，缺少校验链证据时不要 confirmed。
""".strip(),
)
