from django.db import models
from common.fu_model import RootModel


PHASE_SCENARIO_VEHICLE = "vehicle"
PHASE_SCENARIO_COCKPIT = "cockpit"
PHASE_SCENARIO_CHOICES = [
    (PHASE_SCENARIO_VEHICLE, "车控"),
    (PHASE_SCENARIO_COCKPIT, "座舱"),
]


class Project(RootModel):
    name = models.CharField(max_length=255, verbose_name="项目名")
    domain = models.CharField(max_length=255, verbose_name="项目领域")
    type = models.CharField(max_length=255, verbose_name="项目类型")
    code = models.CharField(max_length=255, unique=True, verbose_name="项目编码")
    managers = models.ManyToManyField('core.User', related_name='managed_projects', verbose_name="项目经理")
    is_closed = models.BooleanField(default=False, verbose_name="是否结项")
    repo_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="制品仓号/地址")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    # Switches
    enable_milestone = models.BooleanField(default=True, verbose_name="是否统计里程碑")
    enable_iteration = models.BooleanField(default=True, verbose_name="是否统计迭代数据")
    sub_teams = models.JSONField(default=list, null=True, blank=True, verbose_name="迭代责任团队")
    enable_iteration_quality_metrics = models.BooleanField(
        default=False,
        verbose_name="是否启用迭代代码质量出口指标",
    )
    iteration_quality_oem_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="迭代代码质量OEM名称",
    )
    iteration_quality_module = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="迭代代码质量模块名",
    )

    # Quality
    enable_quality = models.BooleanField(default=False, verbose_name="是否统计代码质量")
    
    # DTS (Issue Tracking)
    enable_dts = models.BooleanField(default=False, verbose_name="是否统计问题单")
    ws_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="数据中台配置ID")
    di_teams = models.JSONField(null=True, blank=True, verbose_name="问题单责任团队")

    # Config Details
    design_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="设计平台ID")

    # Hardware Config
    enable_hardware_config = models.BooleanField(default=False, verbose_name="是否开启典配")
    viu_platform = models.ForeignKey(
        "project_manager.ViuPlatform",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects",
        verbose_name="VIU硬件平台",
    )
    idvp_platform = models.ForeignKey(
        "project_manager.IdvpPlatform",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="projects",
        verbose_name="IDVP软件平台",
    )

    # Favorites
    favorited_by = models.ManyToManyField('core.User', related_name='favorite_projects', blank=True, verbose_name="收藏该项目的用户")

    class Meta:
        db_table = 'pm_project'
        verbose_name = '项目管理'
        verbose_name_plural = verbose_name


class ProjectPhaseConfig(RootModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="phase_configs",
        verbose_name="所属项目",
    )
    stage_name = models.CharField(max_length=128, verbose_name="阶段名称")
    stage_start = models.DateField(null=True, blank=True, verbose_name="阶段开始日期")
    stage_end = models.DateField(null=True, blank=True, verbose_name="阶段结束日期")
    scenario = models.CharField(
        max_length=20,
        choices=PHASE_SCENARIO_CHOICES,
        verbose_name="配置场景",
    )
    vehicle_hardware = models.JSONField(
        default=list,
        blank=True,
        verbose_name="车控硬件组合",
    )
    cdc_platform = models.ForeignKey(
        "project_manager.CdcPlatform",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="phase_configs",
        verbose_name="CDC平台",
    )
    smart_screen_versions = models.ManyToManyField(
        "project_manager.SmartScreenVersion",
        blank=True,
        related_name="phase_configs",
        verbose_name="智慧屏版本",
    )

    class Meta:
        db_table = "pm_project_phase_config"
        verbose_name = "项目阶段典配"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["project", "stage_name"],
                name="uniq_pm_project_stage_name",
            )
        ]
