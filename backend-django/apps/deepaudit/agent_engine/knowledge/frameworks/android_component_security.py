"""Android component exposure and permission guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_COMPONENT_SECURITY = KnowledgeDocument(
    id='android_component_security',
    title='Android 组件暴露与权限边界',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'aosp', 'activity', 'service', 'broadcastreceiver', 'contentprovider', 'manifest', 'permission', 'intent'],
    severity='high',
    content="""
检查重点
- Activity、Service、BroadcastReceiver、ContentProvider 是否在 AndroidManifest.xml 中 exported=true 或因 intent-filter 隐式导出。
- exported 组件是否声明 signature/privileged/custom permission，调用入口是否二次校验 calling uid/package、参数来源和业务状态。
- Provider authority、grantUriPermissions、path-permission、FileProvider paths 是否限制最小范围。
- Broadcast 接收和发送是否使用显式包名、权限、LocalBroadcast 或受控 action，避免被第三方伪造。

证据要求
- finding 必须包含组件名、Manifest/exported/permission 证据、入口方法和可控参数链路。
- 如果 minSdk/targetSdk、系统签名权限、车厂平台白名单或仅系统进程可达能够反驳风险，应降级为 uncertain 或 false_positive。
""".strip(),
)
