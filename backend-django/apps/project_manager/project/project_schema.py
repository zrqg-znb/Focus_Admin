from datetime import date
from typing import List, Optional

from ninja import Field, ModelSchema, Schema

from .project_model import Project


class VehicleHardwareItem(Schema):
    point: str = Field(..., description="硬件点位")
    board: str = Field(..., description="板子型号")
    config_type: str = Field("", description="典配类型")
    bomid: str = Field("", description="BOMID")


class ProjectPhaseConfigIn(Schema):
    stage_name: str = Field(..., description="阶段名称")
    stage_start: Optional[date] = Field(None, description="阶段开始日期")
    stage_end: Optional[date] = Field(None, description="阶段结束日期")
    vehicle_hardware: Optional[List[VehicleHardwareItem]] = Field(
        None, description="车控硬件组合"
    )
    cdc_platform_id: Optional[str] = Field(None, description="CDC平台ID")
    smart_screen_version_id: Optional[str] = Field(None, description="智慧屏版本ID")


class ProjectCreateSchema(Schema):
    name: str = Field(..., description="项目名")
    domain: str = Field(..., description="项目领域")
    type: str = Field(..., description="项目类型")
    code: str = Field(..., description="项目编码")
    manager_ids: List[str] = Field(..., description="项目经理ID列表")
    is_closed: bool = Field(False, description="是否结项")
    repo_url: Optional[str] = Field(None, description="制品仓号/地址")
    remark: Optional[str] = Field(None, description="备注")
    enable_milestone: bool = Field(True, description="是否统计里程碑")
    enable_iteration: bool = Field(True, description="是否统计迭代数据")
    enable_iteration_quality_metrics: bool = Field(
        False,
        description="是否启用健康迭代代码质量出口指标",
    )
    iteration_quality_oem_name: Optional[str] = Field(
        None,
        description="健康迭代代码质量配置OEMName",
    )
    iteration_quality_module: Optional[str] = Field(
        None,
        description="健康迭代代码质量配置模块名",
    )
    enable_quality: bool = Field(True, description="是否统计代码质量")
    enable_dts: bool = Field(False, description="是否统计问题单")
    design_id: Optional[str] = Field(None, description="迭代中台配置 id")
    sub_teams: Optional[List[str]] = Field(None, description="迭代责任团队")
    ws_id: Optional[str] = Field(None, description="数据中台配置ID")
    di_teams: Optional[List[str]] = Field(None, description="问题单责任团队")
    enable_hardware_config: bool = Field(False, description="是否开启典配")
    idvp_platform_id: Optional[str] = Field(None, description="IDVP平台ID")
    phase_configs: Optional[List[ProjectPhaseConfigIn]] = Field(
        None, description="项目阶段典配配置"
    )


class ProjectUpdateSchema(Schema):
    name: Optional[str] = None
    domain: Optional[str] = None
    type: Optional[str] = None
    code: Optional[str] = None
    manager_ids: Optional[List[str]] = None
    is_closed: Optional[bool] = None
    repo_url: Optional[str] = None
    remark: Optional[str] = None
    enable_milestone: Optional[bool] = None
    enable_iteration: Optional[bool] = None
    enable_iteration_quality_metrics: Optional[bool] = None
    iteration_quality_oem_name: Optional[str] = None
    iteration_quality_module: Optional[str] = None
    enable_quality: Optional[bool] = None
    enable_dts: Optional[bool] = None
    design_id: Optional[str] = None
    sub_teams: Optional[List[str]] = None
    ws_id: Optional[str] = None
    di_teams: Optional[List[str]] = None
    enable_hardware_config: Optional[bool] = None
    idvp_platform_id: Optional[str] = None
    phase_configs: Optional[List[ProjectPhaseConfigIn]] = None


class ProjectFilterSchema(Schema):
    keyword: Optional[str] = Field(None, description="搜索关键字(项目名/编码)")
    domain: Optional[str] = None
    type: Optional[str] = None
    manager_id: Optional[str] = Field(None, description="项目经理ID")
    hardware_scenario: Optional[str] = Field(
        None,
        description="典配场景筛选(vehicle/cockpit)",
    )
    is_closed: Optional[bool] = None
    enable_milestone: Optional[bool] = None
    enable_iteration: Optional[bool] = None
    enable_quality: Optional[bool] = None
    enable_dts: Optional[bool] = None
    enable_hardware_config: Optional[bool] = None


class ProjectPhaseConfigOut(Schema):
    id: str
    stage_name: str
    stage_start: Optional[date] = None
    stage_end: Optional[date] = None
    scenario: str
    vehicle_hardware: List[VehicleHardwareItem] = Field(default_factory=list)
    cdc_platform_id: Optional[str] = None
    cdc_platform_name: Optional[str] = None
    smart_screen_version_id: Optional[str] = None
    smart_screen_version_name: Optional[str] = None


class ProjectOut(ModelSchema):
    managers_info: List[dict] = Field([], description="项目经理详情")
    is_favorited: bool = Field(False, description="当前用户是否收藏")
    viu_platform_id: Optional[str] = None
    viu_platform_name: Optional[str] = None
    idvp_platform_id: Optional[str] = None
    idvp_platform_name: Optional[str] = None
    phase_configs: List[ProjectPhaseConfigOut] = Field([], description="阶段典配配置")

    class Meta:
        model = Project
        fields = "__all__"
        exclude = ["managers", "favorited_by", "viu_platform", "idvp_platform"]

    @staticmethod
    def resolve_managers_info(obj):
        return [{"id": m.id, "name": m.name or m.username} for m in obj.managers.all()]

    @staticmethod
    def resolve_is_favorited(obj, context):
        request = context.get("request")
        if request and request.auth:
            return obj.favorited_by.filter(id=request.auth.id).exists()
        return False

    @staticmethod
    def resolve_viu_platform_id(obj):
        return str(obj.viu_platform_id) if obj.viu_platform_id else None

    @staticmethod
    def resolve_viu_platform_name(obj):
        return obj.viu_platform.name if obj.viu_platform else None

    @staticmethod
    def resolve_idvp_platform_id(obj):
        return str(obj.idvp_platform_id) if obj.idvp_platform_id else None

    @staticmethod
    def resolve_idvp_platform_name(obj):
        return obj.idvp_platform.name if obj.idvp_platform else None

    @staticmethod
    def resolve_phase_configs(obj):
        phase_items = list(obj.phase_configs.all())
        phase_items.sort(key=lambda item: (item.stage_start or date.min, item.stage_name))
        return [
            {
                "id": str(item.id),
                "stage_name": item.stage_name,
                "stage_start": item.stage_start,
                "stage_end": item.stage_end,
                "scenario": item.scenario,
                "vehicle_hardware": item.vehicle_hardware or [],
                "cdc_platform_id": (
                    str(item.cdc_platform_id) if item.cdc_platform_id else None
                ),
                "cdc_platform_name": item.cdc_platform.name if item.cdc_platform else None,
                "smart_screen_version_id": (
                    str(item.smart_screen_version_id)
                    if item.smart_screen_version_id
                    else None
                ),
                "smart_screen_version_name": (
                    item.smart_screen_version.name if item.smart_screen_version else None
                ),
            }
            for item in phase_items
        ]

    class Config:
        from_attributes = True
