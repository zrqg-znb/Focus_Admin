"""Android storage, logging and vehicle privacy guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_STORAGE_LOG_PRIVACY = KnowledgeDocument(
    id='android_storage_log_privacy',
    title='Android 存储/日志/车机隐私',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'privacy', 'storage', 'logcat', 'sharedpreferences', 'external_storage', 'vehicle_data'],
    severity='medium',
    content="""
检查重点
- SharedPreferences、SQLite、文件、外部存储、cache、clipboard 是否存储 token、账号、车辆状态、位置、蓝牙/设备标识或诊断数据。
- Log.d/Log.i/printStackTrace 是否输出 PII、VIN、GPS、账号、token、车控状态或调试命令。
- MODE_WORLD_READABLE/WRITEABLE、getExternalStorageDirectory、公共下载目录和宽泛 FileProvider paths 要重点审查。
- 车机多用户、访客模式、售后/工程模式和日志抓取链路可能导致隐私泄露。

证据要求
- 记录数据类型、写入位置、读取方、生命周期、清理策略和是否加密。
- Debug-only、脱敏、仅内存态或受工程开关保护时需作为反例检查。
""".strip(),
)
