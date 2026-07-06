"""Java reflection, classloader and runtime execution guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


JAVA_RUNTIME_REFLECTION_SECURITY = KnowledgeDocument(
    id="java_runtime_reflection_security",
    title="Java 反射/ClassLoader/运行时执行边界",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "java",
        "kotlin",
        "reflection",
        "classloader",
        "dexclassloader",
        "runtime_exec",
        "processbuilder",
        "plugin",
    ],
    severity="high",
    metadata={
        "sources": [
            "Intent/IPC/config/server controlled class or method name",
            "plugin/package/resource loading path",
            "reflection helper API",
            "dynamic dex/jar/apk loader",
        ],
        "sinks": [
            "Class.forName/newInstance/Method.invoke",
            "DexClassLoader/PathClassLoader/URLClassLoader",
            "Runtime.exec/ProcessBuilder",
            "native library loading",
        ],
        "required_context": [
            "source of class/method/path/command",
            "allowlist and signature/hash verification",
            "classloader parent and storage location",
            "process arguments and environment",
        ],
        "false_positive_checks": [
            "class/method name is fixed enum or hardcoded allowlist",
            "plugin package is signature/hash verified",
            "path is app-private and not externally writable",
            "command arguments are fixed and not shell-interpreted",
        ],
        "evidence_examples": [
            "source value -> reflection/classloader sink chain",
            "allowlist or missing allowlist",
            "external storage/plugin path evidence",
            "command construction evidence",
        ],
        "severity_guidance": "外部可控 class/path/command 达到动态加载或执行时 high/critical；固定 allowlist 且签名校验完整时降级。",
    },
    content="""
检查重点
- Class.forName、getMethod/invoke、setAccessible、Proxy、ServiceLoader、DexClassLoader、PathClassLoader、URLClassLoader、Runtime.exec、ProcessBuilder。
- 在 Android/车机场景，动态 dex/plugin/resource/HMI 皮肤包如果来自外部存储、云端、USB 或 Intent URI，必须检查签名、hash 和路径权限。
- 反射命中本身不是漏洞；关键是 class/method/path/command 是否可控，以及是否有 allowlist 和完整性校验。

证据要求
- finding 必须展示输入来源、动态解析/加载/执行 sink、allowlist/签名/路径权限反例检查和影响。
""".strip(),
)
