"""Android WebView and JavaScript bridge guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_WEBVIEW_JSBRIDGE_SECURITY = KnowledgeDocument(
    id='android_webview_jsbridge_security',
    title='Android WebView/JSBridge 安全',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'webview', 'jsbridge', 'javascriptinterface', 'hmi', 'ivi', 'url_loading'],
    severity='high',
    content="""
检查重点
- addJavascriptInterface 暴露对象是否最小化，@JavascriptInterface 方法是否校验来源页面、车机状态和参数。
- setJavaScriptEnabled、setAllowFileAccess、setAllowUniversalAccessFromFileURLs、mixedContentMode、onReceivedSslError 是否被安全配置。
- loadUrl/loadData/loadDataWithBaseURL/evaluateJavascript 输入是否来自外部 Intent、IPC、配置、云端或车机媒体源。
- shouldOverrideUrlLoading 是否限制 scheme/host/path，避免任意跳转、file/content scheme 或本地资源读取。

证据要求
- finding 必须包含 WebView 配置、加载 URL 来源、JSBridge 方法、来源校验和反例检查。
- 仅内部离线页面、固定 allowlist 或系统签名调用链可达时，应降低置信度。
""".strip(),
)
