"""Android crypto and network security guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_CRYPTO_NETWORK_SECURITY = KnowledgeDocument(
    id='android_crypto_network_security',
    title='Android 加密/网络通信安全',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'crypto', 'tls', 'network_security_config', 'okhttp', 'trustmanager', 'hostnameverifier'],
    severity='high',
    content="""
检查重点
- 自定义 TrustManager、HostnameVerifier、onReceivedSslError、OkHttp/HttpURLConnection 配置是否绕过证书和主机名校验。
- network_security_config、cleartextTrafficPermitted、usesCleartextTraffic 是否允许明文通信或 debug CA 进入生产。
- MD5/SHA1/DES/ECB/固定 IV/硬编码密钥/自研加密要结合用途和数据敏感度判断。
- 车机云端、诊断、OTA、账号、地图、语音和远控链路要重点确认 TLS、证书 pinning、重放和 token 生命周期。

证据要求
- 记录网络客户端配置、Manifest/network security config、调用域名、数据类型和反例检查。
- 内网开发环境、debug build 或测试证书需与生产构建条件区分。
""".strip(),
)
