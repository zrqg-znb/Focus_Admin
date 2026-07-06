"""Java parser, XML and serialization boundary guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


JAVA_PARSER_SERIALIZATION_SECURITY = KnowledgeDocument(
    id="java_parser_serialization_security",
    title="Java 解析器/反序列化/XML 安全边界",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "java",
        "kotlin",
        "deserialization",
        "java_deserialization",
        "objectinputstream",
        "xmldecoder",
        "xxe",
        "xml",
        "yaml",
        "json",
    ],
    severity="critical",
    metadata={
        "sources": [
            "network/IPC/file/Intent supplied bytes or XML",
            "downloaded config/resource package",
            "Bluetooth/USB/diagnostic data",
            "server controlled JSON/YAML/XML",
        ],
        "sinks": [
            "ObjectInputStream.readObject/XMLDecoder.readObject",
            "DocumentBuilder/SAXParser/SAXReader/XMLInputFactory",
            "SnakeYAML unsafe load",
            "polymorphic JSON typing",
        ],
        "required_context": [
            "input trust boundary",
            "parser factory security features",
            "class allowlist or object filter",
            "payload size and resource limits",
        ],
        "false_positive_checks": [
            "JEP 290 ObjectInputFilter or strict class allowlist",
            "DTD/external entity disabled and no network resolution",
            "input is signed and integrity verified before parse",
            "parser only handles fixed internal assets",
        ],
        "evidence_examples": [
            "external bytes/XML -> parser sink chain",
            "factory feature configuration",
            "ObjectInputFilter or class resolver evidence",
            "signature/hash verification before parsing",
        ],
        "severity_guidance": "不可信数据进入 Java 反序列化为 critical；XXE 可读文件/SSRF 为 high；内部固定资源且安全特性完整时降级。",
    },
    content="""
检查重点
- ObjectInputStream、XMLDecoder、XStream、SnakeYAML、Jackson default typing、fastjson autoType、DocumentBuilderFactory、SAXParserFactory、XMLInputFactory。
- Android/车机项目常见输入来自云端配置、USB/蓝牙、诊断文件、HMI 资源包、地图/语音包，不要只按 Web 请求判断可达性。
- XML 安全要看 disallow-doctype-decl、external-general/entities、external-parameter/entities、load-external-dtd、ACCESS_EXTERNAL_DTD/SCHEMA。
- 反序列化安全要看 ObjectInputFilter、class allowlist、签名/完整性、资源限制。

证据要求
- finding 需要输入来源、parser/deserialize sink、安全特性或缺失证据、反例检查和影响。
""".strip(),
)
