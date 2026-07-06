"""Android Vehicle HAL and CarService boundary guidance."""

from ..base import KnowledgeCategory, KnowledgeDocument


ANDROID_VEHICLE_HAL_CAR_SERVICE_SECURITY = KnowledgeDocument(
    id="android_vehicle_hal_car_service_security",
    title="Android Vehicle HAL/CarService 属性边界",
    category=KnowledgeCategory.FRAMEWORK,
    tags=[
        "android",
        "automotive",
        "vehicle_hal",
        "vhal",
        "car_service",
        "carpropertymanager",
        "vehicle_property",
        "hal",
    ],
    severity="critical",
    metadata={
        "sources": [
            "CarPropertyManager/VehicleProperty access",
            "CarService Binder entry",
            "Vehicle HAL Java/native bridge",
            "vehicle property listener callbacks",
        ],
        "sinks": [
            "setProperty/write vehicle property",
            "HVAC, door, seat, power, cluster or ADAS state update",
            "subscribe vehicle data stream",
            "native VHAL command",
        ],
        "required_context": [
            "property ID and access mode",
            "caller permission and area ID",
            "vehicle state constraints",
            "HAL/native enforcement and feature config",
        ],
        "false_positive_checks": [
            "property is read-only or mock/test-only",
            "CarService enforces signature permission and area policy",
            "HAL validates property range and vehicle state",
            "feature config excludes the property on target model",
        ],
        "evidence_examples": [
            "component/Binder entry -> CarPropertyManager.setProperty chain",
            "permission check for property ID",
            "vehicle speed/gear/power guard",
            "VHAL config or native validation evidence",
        ],
        "severity_guidance": "低权限入口可写车辆控制/HMI 安全属性时 critical；只读数据且权限/车型配置完整时降级。",
    },
    content="""
检查重点
- CarPropertyManager、VehiclePropertyIds、CarService、VHAL/native bridge 连接了应用层与车辆状态，不是普通 Java getter/setter。
- 写属性、订阅高频车辆数据、HMI/cluster 状态更新必须检查权限、areaId、车型配置、车辆状态和 native/HAL 二次校验。
- Mock HAL、emulator、test property、debug feature flag 容易造成误报，必须读取配置或构建条件。

证据要求
- finding 需要属性 ID/名称、入口链路、权限和车辆状态约束、HAL/native 反例检查、实际影响。
- 缺少属性语义或车型配置时降级为 uncertain。
""".strip(),
)
