"""Android JNI/native boundary guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_JNI_NATIVE_BOUNDARY = KnowledgeDocument(
    id='android_jni_native_boundary',
    title='Android JNI/Native 边界',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'jni', 'native', 'ndk', 'hal', 'vehicle', 'thread'],
    severity='high',
    content="""
检查重点
- System.loadLibrary、native 方法、JNIEnv 字符串/数组访问、DirectByteBuffer、Bitmap/Surface 传递是否校验长度、生命周期和线程归属。
- Java 层传入 native 的路径、命令、JSON、图片帧、显示参数、车辆状态是否做边界检查。
- native 回调到 Java/HMI 线程时是否正确切主线程、处理异常和释放 local/global references。
- JNI 与 HAL/车控 native 服务交互时必须确认权限、SELinux、进程边界和失败降级。

证据要求
- 记录 Java native 声明、loadLibrary、参数来源、native sink 或回调路径。
- 缺少 native 实现或编译变体证据时，结论应为 uncertain。
""".strip(),
)
