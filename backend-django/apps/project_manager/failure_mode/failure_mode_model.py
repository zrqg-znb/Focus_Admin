from django.db import models
from django.utils import timezone

from common.fu_model import RootModel


class FailureMode(RootModel):
    SOURCE_TYPE_MANUAL = 'manual'
    SOURCE_TYPE_TASK_QUICK_CREATE = 'task_quick_create'
    SOURCE_TYPE_CHOICES = [
        (SOURCE_TYPE_MANUAL, '手动维护'),
        (SOURCE_TYPE_TASK_QUICK_CREATE, '任务新增'),
    ]

    brief = models.CharField(max_length=255, verbose_name='故障模式简述')
    subsystem = models.CharField(max_length=128, blank=True, null=True, verbose_name='子系统')
    module_name = models.CharField(max_length=128, blank=True, null=True, verbose_name='模块')
    chips = models.JSONField(default=list, blank=True, verbose_name='芯片')
    fault_categories = models.JSONField(default=list, blank=True, verbose_name='故障类别')
    symptoms = models.JSONField(default=list, blank=True, verbose_name='故障现象')
    effect_html = models.TextField(blank=True, default='', verbose_name='故障影响')
    root_cause_html = models.TextField(blank=True, default='', verbose_name='故障根因')
    functional_safety_level = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='功能安全等级',
    )
    occurrence_frequency = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name='故障发生频度',
    )
    detectability = models.CharField(
        max_length=32,
        blank=True,
        null=True,
        verbose_name='故障可探测度',
    )
    severity = models.CharField(max_length=32, blank=True, null=True, verbose_name='严重程度')
    related_dts_nos = models.JSONField(default=list, blank=True, verbose_name='关联问题单')
    scope_bindings = models.JSONField(default=list, blank=True, verbose_name='产品范围绑定')
    status = models.CharField(max_length=64, blank=True, null=True, verbose_name='状态')
    source_type = models.CharField(
        max_length=32,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_TYPE_MANUAL,
        db_index=True,
        verbose_name='来源类型',
    )
    source_task = models.ForeignKey(
        'FailureModeTask',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_failure_modes',
        verbose_name='来源任务',
    )
    interception_required = models.BooleanField(default=False, verbose_name='需要产线拦截策略')
    huatuo_required = models.BooleanField(default=False, verbose_name='需要华佗诊断方案')
    required_handling_measure_categories = models.JSONField(
        default=list,
        blank=True,
        verbose_name='必配故障处理措施类别',
    )
    required_observation_method_types = models.JSONField(
        default=list,
        blank=True,
        verbose_name='必配维测手段类型',
    )
    authors = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_modes',
        verbose_name='作者',
    )

    class Meta:
        db_table = 'pm_failure_mode'
        verbose_name = '故障模式'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['brief'], name='idx_pm_fm_brief'),
            models.Index(fields=['subsystem', 'status'], name='idx_pm_fm_sub_status'),
            models.Index(fields=['module_name'], name='idx_pm_fm_module'),
            models.Index(fields=['source_type', 'source_task'], name='idx_pm_fm_source_task'),
        ]


class FailureModeSubsystemConfig(RootModel):
    subsystem = models.CharField(max_length=128, unique=True, verbose_name='子系统')
    module_options = models.JSONField(default=list, blank=True, verbose_name='模块选项')
    chip_options = models.JSONField(default=list, blank=True, verbose_name='芯片选项')

    class Meta:
        db_table = 'pm_failure_mode_subsystem_config'
        verbose_name = '故障模式子系统联动配置'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['subsystem'], name='idx_pm_fm_sub_cfg_subsystem')]


class InterceptionStrategy(RootModel):
    interception_item = models.CharField(max_length=255, verbose_name='产线拦截项')
    version_detection_html = models.TextField(blank=True, default='', verbose_name='产线版本检测方案')
    station = models.CharField(max_length=255, blank=True, null=True, verbose_name='工位')
    owners = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_interception_strategies',
        verbose_name='设计责任人',
    )

    class Meta:
        db_table = 'pm_failure_interception_strategy'
        verbose_name = '产线拦截策略'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['interception_item'], name='idx_pm_fm_inter_item')]


class HandlingMeasure(RootModel):
    measure_category = models.CharField(max_length=128, blank=True, null=True, verbose_name='措施类别')
    measure = models.CharField(max_length=255, verbose_name='处理措施')
    measure_detail_html = models.TextField(blank=True, default='', verbose_name='处理措施详情')
    measure_effect = models.TextField(blank=True, default='', verbose_name='措施影响')
    owners = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_handling_measures',
        verbose_name='设计责任人',
    )

    class Meta:
        db_table = 'pm_failure_handling_measure'
        verbose_name = '故障处理措施'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['measure'], name='idx_pm_fm_measure')]


class ObservationMethod(RootModel):
    monitor_type = models.CharField(max_length=128, blank=True, null=True, verbose_name='维测类型')
    log_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='日志ID')
    log_keyword = models.CharField(max_length=255, blank=True, null=True, verbose_name='日志关键词')
    log_path = models.CharField(max_length=512, blank=True, null=True, verbose_name='日志获取路径')
    owners = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_observation_methods',
        verbose_name='设计责任人',
    )

    class Meta:
        db_table = 'pm_failure_observation_method'
        verbose_name = '维测手段'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['monitor_type'], name='idx_pm_fm_monitor_type'),
            models.Index(fields=['log_id'], name='idx_pm_fm_log_id'),
        ]


class HuatuoDiagnosis(RootModel):
    description = models.TextField(verbose_name='诊断方案描述')
    owners = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_huatuo_diagnoses',
        verbose_name='设计责任人',
    )

    class Meta:
        db_table = 'pm_failure_huatuo_diagnosis'
        verbose_name = '华佗诊断方案'
        verbose_name_plural = verbose_name


class TestCase(RootModel):
    brief = models.CharField(max_length=255, verbose_name='测试用例简述')
    detail_html = models.TextField(blank=True, default='', verbose_name='测试用例详情')
    cida_link = models.CharField(max_length=512, blank=True, null=True, verbose_name='CIDA链接')
    owners = models.ManyToManyField(
        'core.User',
        blank=True,
        related_name='failure_test_cases',
        verbose_name='设计责任人',
    )

    class Meta:
        db_table = 'pm_failure_test_case'
        verbose_name = '测试用例'
        verbose_name_plural = verbose_name
        indexes = [models.Index(fields=['brief'], name='idx_pm_fm_test_case')]


class FailureModeInterceptionStrategyRel(RootModel):
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='interception_relations',
        verbose_name='故障模式',
    )
    interception_strategy = models.ForeignKey(
        InterceptionStrategy,
        on_delete=models.CASCADE,
        related_name='failure_mode_relations',
        verbose_name='产线拦截策略',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_failure_mode_interception_rel'
        verbose_name = '故障模式-产线拦截策略关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['failure_mode', 'interception_strategy'],
                name='uniq_pm_fm_inter_rel',
            )
        ]
        indexes = [models.Index(fields=['failure_mode', 'order_index'], name='idx_pm_fm_inter_rel')]


class FailureModeHandlingMeasureRel(RootModel):
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='handling_measure_relations',
        verbose_name='故障模式',
    )
    handling_measure = models.ForeignKey(
        HandlingMeasure,
        on_delete=models.CASCADE,
        related_name='failure_mode_relations',
        verbose_name='故障处理措施',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_failure_mode_measure_rel'
        verbose_name = '故障模式-故障处理措施关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['failure_mode', 'handling_measure'],
                name='uniq_pm_fm_measure_rel',
            )
        ]
        indexes = [models.Index(fields=['failure_mode', 'order_index'], name='idx_pm_fm_measure_rel')]


class FailureModeObservationMethodRel(RootModel):
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='observation_method_relations',
        verbose_name='故障模式',
    )
    observation_method = models.ForeignKey(
        ObservationMethod,
        on_delete=models.CASCADE,
        related_name='failure_mode_relations',
        verbose_name='维测手段',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_failure_mode_observation_rel'
        verbose_name = '故障模式-维测手段关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['failure_mode', 'observation_method'],
                name='uniq_pm_fm_observation_rel',
            )
        ]
        indexes = [models.Index(fields=['failure_mode', 'order_index'], name='idx_pm_fm_observe_rel')]


class FailureModeHuatuoDiagnosisRel(RootModel):
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='huatuo_diagnosis_relations',
        verbose_name='故障模式',
    )
    huatuo_diagnosis = models.ForeignKey(
        HuatuoDiagnosis,
        on_delete=models.CASCADE,
        related_name='failure_mode_relations',
        verbose_name='华佗诊断方案',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_failure_mode_huatuo_rel'
        verbose_name = '故障模式-华佗诊断方案关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['failure_mode', 'huatuo_diagnosis'],
                name='uniq_pm_fm_huatuo_rel',
            )
        ]
        indexes = [models.Index(fields=['failure_mode', 'order_index'], name='idx_pm_fm_huatuo_rel')]


class HandlingMeasureTestCaseRel(RootModel):
    handling_measure = models.ForeignKey(
        HandlingMeasure,
        on_delete=models.CASCADE,
        related_name='test_case_relations',
        verbose_name='故障处理措施',
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='handling_measure_relations',
        verbose_name='测试用例',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_failure_measure_test_case_rel'
        verbose_name = '故障处理措施-测试用例关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['handling_measure', 'test_case'],
                name='uniq_pm_fm_test_case_rel',
            )
        ]
        indexes = [models.Index(fields=['handling_measure', 'order_index'], name='idx_pm_fm_test_rel')]


class FailureModeProduct(RootModel):
    project = models.OneToOneField(
        'project_manager.Project',
        on_delete=models.CASCADE,
        related_name='failure_mode_product',
        verbose_name='关联产品(项目)'
    )
    owner = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_failure_mode_products',
        verbose_name='产品归属人(版本SE)'
    )

    class Meta:
        db_table = 'pm_failure_mode_product'
        verbose_name = '产品故障模式配置'
        verbose_name_plural = verbose_name


class ProductFailureMode(RootModel):
    product = models.ForeignKey(
        FailureModeProduct,
        on_delete=models.CASCADE,
        related_name='bound_failure_modes',
        verbose_name='所属产品'
    )
    subsystem = models.CharField(max_length=128, verbose_name='子系统')
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='product_bindings',
        verbose_name='故障模式'
    )
    is_landed = models.BooleanField(default=False, verbose_name='故障模式是否已落地')

    class Meta:
        db_table = 'pm_product_failure_mode'
        verbose_name = '产品故障模式基线'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'subsystem', 'failure_mode'],
                name='uniq_pm_product_fm'
            )
        ]
        indexes = [
            models.Index(fields=['product', 'subsystem'], name='idx_pm_prod_fm_subsys')
        ]


class ProductFailureModeInterceptionStrategyRel(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='interception_relations',
        verbose_name='产品故障模式基线',
    )
    interception_strategy = models.ForeignKey(
        InterceptionStrategy,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_relations',
        verbose_name='产线拦截策略',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_product_fm_interception_rel'
        verbose_name = '产品故障模式-产线拦截策略关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'interception_strategy'],
                name='uniq_pm_prod_fm_inter_rel',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode', 'order_index'],
                name='idx_pm_prod_fm_inter_rel',
            )
        ]


class ProductFailureModeHandlingMeasureRel(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='handling_measure_relations',
        verbose_name='产品故障模式基线',
    )
    handling_measure = models.ForeignKey(
        HandlingMeasure,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_relations',
        verbose_name='故障处理措施',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_product_fm_measure_rel'
        verbose_name = '产品故障模式-故障处理措施关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'handling_measure'],
                name='uniq_pm_prod_fm_measure_rel',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode', 'order_index'],
                name='idx_pm_prod_fm_measure_rel',
            )
        ]


class ProductFailureModeObservationMethodRel(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='observation_method_relations',
        verbose_name='产品故障模式基线',
    )
    observation_method = models.ForeignKey(
        ObservationMethod,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_relations',
        verbose_name='维测手段',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_product_fm_observation_rel'
        verbose_name = '产品故障模式-维测手段关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'observation_method'],
                name='uniq_pm_prod_fm_observation_rel',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode', 'order_index'],
                name='idx_pm_prod_fm_observe_rel',
            )
        ]


class ProductFailureModeHuatuoDiagnosisRel(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='huatuo_diagnosis_relations',
        verbose_name='产品故障模式基线',
    )
    huatuo_diagnosis = models.ForeignKey(
        HuatuoDiagnosis,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_relations',
        verbose_name='华佗诊断方案',
    )
    order_index = models.IntegerField(default=0, verbose_name='排序')

    class Meta:
        db_table = 'pm_product_fm_huatuo_rel'
        verbose_name = '产品故障模式-华佗诊断方案关联'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'huatuo_diagnosis'],
                name='uniq_pm_prod_fm_huatuo_rel',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode', 'order_index'],
                name='idx_pm_prod_fm_huatuo_rel',
            )
        ]


class ProductFailureModeInterceptionLanding(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='interception_landings',
        verbose_name='产品故障模式基线',
    )
    interception_strategy = models.ForeignKey(
        InterceptionStrategy,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_landings',
        verbose_name='产线拦截策略',
    )
    is_landed = models.BooleanField(default=False, verbose_name='是否已落地')

    class Meta:
        db_table = 'pm_product_fm_interception_landing'
        verbose_name = '产品故障模式-产线拦截策略落地'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'interception_strategy'],
                name='uniq_pm_prod_fm_inter_landing',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode'],
                name='idx_pfmil_pfm',
            ),
            models.Index(
                fields=['interception_strategy'],
                name='idx_pfmil_item',
            ),
        ]


class ProductFailureModeHandlingLanding(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='handling_landings',
        verbose_name='产品故障模式基线',
    )
    handling_measure = models.ForeignKey(
        HandlingMeasure,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_landings',
        verbose_name='故障处理措施',
    )
    is_landed = models.BooleanField(default=False, verbose_name='是否已落地')

    class Meta:
        db_table = 'pm_product_fm_handling_landing'
        verbose_name = '产品故障模式-故障处理措施落地'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'handling_measure'],
                name='uniq_pm_prod_fm_handling_landing',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode'],
                name='idx_pfmhl_pfm',
            ),
            models.Index(
                fields=['handling_measure'],
                name='idx_pfmhl_item',
            ),
        ]


class ProductFailureModeObservationLanding(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='observation_landings',
        verbose_name='产品故障模式基线',
    )
    observation_method = models.ForeignKey(
        ObservationMethod,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_landings',
        verbose_name='维测手段',
    )
    is_landed = models.BooleanField(default=False, verbose_name='是否已落地')

    class Meta:
        db_table = 'pm_product_fm_observation_landing'
        verbose_name = '产品故障模式-维测手段落地'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'observation_method'],
                name='uniq_pm_prod_fm_observation_landing',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode'],
                name='idx_pfmol_pfm',
            ),
            models.Index(
                fields=['observation_method'],
                name='idx_pfmol_item',
            ),
        ]


class ProductFailureModeHuatuoLanding(RootModel):
    product_failure_mode = models.ForeignKey(
        ProductFailureMode,
        on_delete=models.CASCADE,
        related_name='huatuo_landings',
        verbose_name='产品故障模式基线',
    )
    huatuo_diagnosis = models.ForeignKey(
        HuatuoDiagnosis,
        on_delete=models.CASCADE,
        related_name='product_failure_mode_landings',
        verbose_name='华佗诊断方案',
    )
    is_landed = models.BooleanField(default=False, verbose_name='是否已落地')

    class Meta:
        db_table = 'pm_product_fm_huatuo_landing'
        verbose_name = '产品故障模式-华佗诊断方案落地'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['product_failure_mode', 'huatuo_diagnosis'],
                name='uniq_pm_prod_fm_huatuo_landing',
            )
        ]
        indexes = [
            models.Index(
                fields=['product_failure_mode'],
                name='idx_pfmul_pfm',
            ),
            models.Index(
                fields=['huatuo_diagnosis'],
                name='idx_pfmul_item',
            ),
        ]


class FailureModeTask(RootModel):
    TASK_TYPE_CHOICES = [
        ('CREATE', '创建'),
        ('REVISE', '修订'),
        ('DELETE', '删除'),
    ]
    STATUS_CHOICES = [
        ('CREATED', '创建'),
        ('PROCESSING', '梳理/修订中'),
        ('REVIEWING', '评审中'),
        ('CLOSED', '已关闭'),
    ]
    REVIEW_RESULT_CHOICES = [
        ('approved', '通过'),
        ('rejected', '驳回'),
    ]
    task_no = models.CharField(max_length=64, blank=True, default='', db_index=True, verbose_name='任务编号')
    name = models.CharField(max_length=255, verbose_name='任务名称')
    task_type = models.CharField(max_length=32, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='CREATED', verbose_name='任务状态')
    product = models.ForeignKey(
        FailureModeProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name='关联产品'
    )
    subsystem = models.CharField(max_length=128, blank=True, null=True, verbose_name='子系统')
    creator = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_fm_tasks',
        verbose_name='创建人(版本SE)'
    )
    assignee = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_fm_tasks',
        verbose_name='责任人(特性SE)'
    )
    current_processor = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_processing_fm_tasks',
        verbose_name='当前待办归属人',
    )
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name='接收时间')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交评审时间')
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='评审完成时间')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='关闭时间')
    review_result = models.CharField(
        max_length=32,
        choices=REVIEW_RESULT_CHOICES,
        blank=True,
        default='',
        verbose_name='评审结果',
    )
    review_minutes_html = models.TextField(blank=True, default='', verbose_name='评审会议纪要')
    review_attachment_ids = models.JSONField(default=list, blank=True, verbose_name='评审附件')
    baseline_snapshot_ids = models.JSONField(default=list, blank=True, verbose_name='任务创建时基线快照')

    class Meta:
        db_table = 'pm_failure_mode_task'
        verbose_name = '故障模式梳理任务'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['status'], name='idx_pm_fm_task_status'),
            models.Index(fields=['assignee', 'status'], name='idx_pm_fm_task_assignee'),
            models.Index(fields=['current_processor', 'status'], name='idx_pm_fm_task_processor'),
        ]

    def save(self, *args, **kwargs):
        if not self.task_no:
            self.task_no = timezone.now().strftime('FMT%Y%m%d%H%M%S%f')
        super().save(*args, **kwargs)


class TaskFailureMode(RootModel):
    task = models.ForeignKey(
        FailureModeTask,
        on_delete=models.CASCADE,
        related_name='task_failure_modes',
        verbose_name='关联任务'
    )
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='task_bindings',
        verbose_name='故障模式'
    )
    landing_payload_json = models.JSONField(default=dict, blank=True, verbose_name='任务内落地草稿')

    class Meta:
        db_table = 'pm_task_failure_mode'
        verbose_name = '任务关联故障模式'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['task', 'failure_mode'],
                name='uniq_pm_task_fm'
            )
        ]


class FailureModeTaskDraft(RootModel):
    task = models.ForeignKey(
        FailureModeTask,
        on_delete=models.CASCADE,
        related_name='drafts',
        verbose_name='关联任务',
    )
    failure_mode = models.ForeignKey(
        FailureMode,
        on_delete=models.CASCADE,
        related_name='task_drafts',
        verbose_name='故障模式',
    )
    draft_payload_json = models.JSONField(default=dict, blank=True, verbose_name='任务修订草稿')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否生效')

    class Meta:
        db_table = 'pm_failure_mode_task_draft'
        verbose_name = '故障模式任务修订草稿'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['task', 'failure_mode'],
                name='uniq_pm_task_failure_mode_draft',
            )
        ]
        indexes = [
            models.Index(fields=['task', 'is_active'], name='idx_pm_fm_task_draft_task'),
            models.Index(fields=['failure_mode', 'is_active'], name='idx_pm_fm_task_draft_fm'),
        ]


class FailureModeRoleAssignment(RootModel):
    ROLE_FM_ADMIN = 'fm_admin'
    ROLE_VERSION_SE = 'version_se'
    ROLE_FEATURE_SE = 'feature_se'
    ROLE_MEMBER = 'member'
    ROLE_CHOICES = [
        (ROLE_FM_ADMIN, '管理员'),
        (ROLE_VERSION_SE, '版本SE'),
        (ROLE_FEATURE_SE, '特性SE'),
        (ROLE_MEMBER, '普通成员'),
    ]

    user = models.ForeignKey(
        'core.User',
        on_delete=models.CASCADE,
        related_name='failure_mode_role_assignments',
        verbose_name='用户',
    )
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, db_index=True, verbose_name='角色')
    product = models.ForeignKey(
        FailureModeProduct,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='role_assignments',
        verbose_name='关联产品',
    )
    subsystem = models.CharField(max_length=128, blank=True, default='', verbose_name='子系统')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        db_table = 'pm_failure_mode_role_assignment'
        verbose_name = '故障模式角色授权'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'role', 'product', 'subsystem'],
                name='uniq_pm_fm_role_assignment',
            )
        ]
        indexes = [
            models.Index(fields=['user', 'is_active'], name='idx_pm_fm_role_user_active'),
            models.Index(fields=['product', 'role', 'subsystem'], name='idx_pm_fm_role_scope'),
        ]


class FailureModeTaskLog(RootModel):
    ACTION_CREATE = 'create'
    ACTION_ACCEPT = 'accept'
    ACTION_BIND_FAILURE_MODES = 'bind_failure_modes'
    ACTION_QUICK_CREATE_FAILURE_MODE = 'quick_create_failure_mode'
    ACTION_EDIT_FAILURE_MODE = 'edit_failure_mode'
    ACTION_SAVE_LANDING = 'save_landing'
    ACTION_SAVE_DRAFT = 'save_draft'
    ACTION_DELETE_DRAFT = 'delete_draft'
    ACTION_UPDATE_SCOPE = 'update_scope'
    ACTION_SUBMIT = 'submit'
    ACTION_RECALL = 'recall'
    ACTION_REJECT = 'reject'
    ACTION_CLOSE = 'close'
    ACTION_REASSIGN = 'reassign'
    ACTION_CHOICES = [
        (ACTION_CREATE, '创建任务'),
        (ACTION_ACCEPT, '接收任务'),
        (ACTION_BIND_FAILURE_MODES, '绑定故障模式'),
        (ACTION_QUICK_CREATE_FAILURE_MODE, '快速新增故障模式'),
        (ACTION_EDIT_FAILURE_MODE, '编辑任务内故障模式'),
        (ACTION_SAVE_LANDING, '保存落地配置'),
        (ACTION_SAVE_DRAFT, '保存修订草稿'),
        (ACTION_DELETE_DRAFT, '撤销修订草稿'),
        (ACTION_UPDATE_SCOPE, '补齐工作范围'),
        (ACTION_SUBMIT, '提交评审'),
        (ACTION_RECALL, '撤回评审'),
        (ACTION_REJECT, '驳回任务'),
        (ACTION_CLOSE, '评审关闭'),
        (ACTION_REASSIGN, '改派责任人'),
    ]

    task = models.ForeignKey(
        FailureModeTask,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='任务',
    )
    action = models.CharField(max_length=64, choices=ACTION_CHOICES, db_index=True, verbose_name='动作')
    from_status = models.CharField(max_length=32, blank=True, default='', verbose_name='原状态')
    to_status = models.CharField(max_length=32, blank=True, default='', verbose_name='新状态')
    operator = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='failure_mode_task_logs',
        verbose_name='操作人',
    )
    note = models.TextField(blank=True, default='', verbose_name='备注')
    extra_data = models.JSONField(default=dict, blank=True, verbose_name='扩展数据')

    class Meta:
        db_table = 'pm_failure_mode_task_log'
        verbose_name = '故障模式任务日志'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['task', 'sys_create_datetime'], name='idx_pm_fm_task_log_time'),
            models.Index(fields=['action', 'sys_create_datetime'], name='idx_pm_fm_task_log_action'),
        ]
