"""Android cockpit HMI/display state guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_HMI_DISPLAY_STATE = KnowledgeDocument(
    id='android_hmi_display_state',
    title='车机座舱/HMI 显示状态安全',
    category=KnowledgeCategory.FRAMEWORK,
    tags=['android', 'hmi', 'cockpit', 'ivi', 'display', 'surface', 'cluster', 'vehicle_state'],
    severity='medium',
    content="""
检查重点
- 仪表、HUD、中控、告警、倒车影像、ADAS 提示等显示链路是否有状态优先级、遮挡、超时、刷新和异常降级策略。
- SurfaceView/TextureView/GLSurfaceView/Canvas/RecyclerView/动画状态是否可能因异步回调、跨线程更新或生命周期切换出现旧状态残留。
- 车辆速度、档位、告警、驾驶模式、主题/亮度/多屏同步等状态源是否有可信来源和时序约束。
- HMI 显示问题不应只按 UI bug 处理；涉及驾驶安全提示、遮挡、错误状态或延迟显示时需要保留风险备注。

证据要求
- 记录状态来源、UI 更新入口、线程/生命周期、显示 sink、优先级/降级逻辑和反例检查。
- 仅测试页面、demo 模式、不可达车型配置或受 feature flag 禁用时应降级。
""".strip(),
)
