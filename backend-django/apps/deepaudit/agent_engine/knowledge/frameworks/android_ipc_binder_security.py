"""Android Binder and IPC guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_IPC_BINDER_SECURITY = KnowledgeDocument(
    id='android_ipc_binder_security',
    title='Android Binder/IPC 身份校验',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'aosp', 'binder', 'aidl', 'ipc', 'messenger', 'pendingintent', 'permission'],
    severity='high',
    content="""
检查重点
- Binder/AIDL/Messenger/ResultReceiver/PendingIntent 入口是否校验 Binder.getCallingUid/getCallingPid、调用包名、签名权限或 SELinux/系统进程边界。
- clearCallingIdentity/restoreCallingIdentity 是否成对出现，是否把调用者身份错误提升为系统身份。
- Parcelable/Bundle/Intent extra 是否进行类型、范围、空值和权限校验。
- PendingIntent 是否 mutable、隐式 Intent 或缺少 requestCode/flags 约束。

证据要求
- 记录 IPC 入口、调用者身份来源、权限校验点、敏感操作 sink 和反例检查。
- 缺少调用身份或权限证据时，不要把单个 Binder 方法直接判为 confirmed。
""".strip(),
)
