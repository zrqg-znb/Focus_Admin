from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project


class IntegrationProjectConfig(RootModel):
    project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        related_name="integration_configs",
        verbose_name="所属项目",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=128, verbose_name="配置名称/邮件显示名")
    managers = models.ManyToManyField(
        "core.User",
        related_name="integration_configs_managed",
        verbose_name="项目负责人",
        blank=True,
    )
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    code_check_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="代码检测任务ID")
    dt_bin_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="DT_Bin任务ID")
    cooddy_check_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="Cooddy Check任务ID")
    bin_scope_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="二进制范围任务ID")
    enable_domain_metrics = models.BooleanField(default=False, verbose_name="是否按责任田领域获取")
    domain_directory_set = models.ForeignKey(
        "IntegrationDomainDirectorySet",
        on_delete=models.SET_NULL,
        related_name="project_configs",
        verbose_name="责任田目录配置集",
        null=True,
        blank=True,
    )
    code_check_task_ids = models.JSONField(default=list, blank=True, verbose_name="CodeCheck任务ID列表")
    dt_bin_task_ids = models.JSONField(default=list, blank=True, verbose_name="DT_Bin任务ID列表")
    cooddy_check_task_ids = models.JSONField(default=list, blank=True, verbose_name="Cooddy Check任务ID列表")
    bin_scope_task_ids = models.JSONField(default=list, blank=True, verbose_name="Bin Scope任务ID列表")
    build_check_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="构建检测任务ID")
    compile_check_task_id = models.CharField(max_length=128, blank=True, default="", verbose_name="编译检测任务ID")
    dt_project_id = models.CharField(max_length=128, blank=True, default="", verbose_name="DT项目ID")
    code_scan_project_key = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="代码扫描项目Key",
    )
    valgrind_sub_modules = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Valgrind子模块列表",
    )
    enable_dt_fuzz = models.BooleanField(default=False, verbose_name="是否启用DT_FUZZ")
    dt_fuzz_version_name = models.CharField(max_length=128, blank=True, default="", verbose_name="DT_FUZZ版本名")
    dt_fuzz_branches = models.JSONField(default=list, blank=True, verbose_name="DT_FUZZ分支列表")
    dt_fuzz_pbi_id = models.CharField(max_length=128, blank=True, default="", verbose_name="DT_FUZZ PBI ID")
    dt_fuzz_domain_id = models.CharField(max_length=128, blank=True, default="", verbose_name="DT_FUZZ Domain ID")
    dt_fuzz_project_id = models.CharField(max_length=128, blank=True, default="", verbose_name="DT_FUZZ Project ID")

    class Meta:
        db_table = "ir_project_config"
        verbose_name = "每日集成报告项目配置"
        verbose_name_plural = verbose_name


class IntegrationDomainDirectorySet(RootModel):
    name = models.CharField(max_length=128, verbose_name="配置集名称")
    description = models.TextField(blank=True, default="", verbose_name="说明")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "ir_domain_directory_set"
        verbose_name = "集成报告责任田目录配置集"
        verbose_name_plural = verbose_name


class IntegrationDomainDirectoryRule(RootModel):
    directory_set = models.ForeignKey(
        IntegrationDomainDirectorySet,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name="配置集",
    )
    domain_name = models.CharField(max_length=128, verbose_name="责任田领域")
    directory = models.CharField(max_length=512, verbose_name="目录字符串")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "ir_domain_directory_rule"
        verbose_name = "集成报告责任田目录规则"
        verbose_name_plural = verbose_name
        ordering = ("sort_order", "sys_create_datetime")


class IntegrationMetricDefinition(RootModel):
    group = models.CharField(max_length=64, verbose_name="分组")  # code | dt
    key = models.CharField(max_length=128, unique=True, verbose_name="指标Key")
    name = models.CharField(max_length=128, verbose_name="指标名称")
    value_type = models.CharField(max_length=32, default="number", verbose_name="值类型")  # number|string|percent
    unit = models.CharField(max_length=16, blank=True, default="", verbose_name="单位")

    warn_operator = models.CharField(max_length=8, blank=True, default="", verbose_name="预警操作符")  # > < >= <= != ==
    warn_value = models.FloatField(null=True, blank=True, verbose_name="预警阈值")
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "ir_metric_definition"
        verbose_name = "每日集成报告指标定义"
        verbose_name_plural = verbose_name


class IntegrationProjectMetricValue(RootModel):
    config = models.ForeignKey(
        IntegrationProjectConfig,
        on_delete=models.CASCADE,
        related_name="metric_values",
        verbose_name="所属配置",
    )
    record_date = models.DateField(verbose_name="记录日期")
    metric = models.ForeignKey(
        IntegrationMetricDefinition,
        on_delete=models.CASCADE,
        related_name="values",
        verbose_name="指标",
    )
    value_number = models.FloatField(null=True, blank=True, verbose_name="数值")
    value_text = models.CharField(max_length=255, blank=True, default="", verbose_name="文本值")
    detail_url = models.CharField(max_length=512, blank=True, default="", verbose_name="详情URL")

    class Meta:
        db_table = "ir_project_metric_value"
        verbose_name = "每日集成报告项目指标值"
        verbose_name_plural = verbose_name
        unique_together = ("config", "record_date", "metric")


class IntegrationDtFuzzSnapshot(RootModel):
    config = models.ForeignKey(
        IntegrationProjectConfig,
        on_delete=models.CASCADE,
        related_name="dt_fuzz_snapshots",
        verbose_name="所属配置",
    )
    record_date = models.DateField(verbose_name="记录日期")
    source_due_date = models.CharField(max_length=32, blank=True, default="", verbose_name="数据湖DueDate")
    branch = models.CharField(max_length=128, verbose_name="分支")
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name="原始载荷")
    tree_payload = models.JSONField(default=dict, blank=True, verbose_name="树形载荷")

    class Meta:
        db_table = "ir_dt_fuzz_snapshot"
        verbose_name = "每日集成报告DT_FUZZ快照"
        verbose_name_plural = verbose_name
        unique_together = ("config", "record_date", "branch")


class IntegrationEmailSubscription(RootModel):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE, related_name="integration_subscriptions", verbose_name="订阅人")
    config = models.ForeignKey(
        IntegrationProjectConfig,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="订阅配置",
    )
    enabled = models.BooleanField(default=True, verbose_name="是否启用")

    class Meta:
        db_table = "ir_email_subscription"
        verbose_name = "每日集成报告邮件订阅"
        verbose_name_plural = verbose_name
        unique_together = ("user", "config")


class IntegrationEmailDelivery(RootModel):
    record_date = models.DateField(verbose_name="数据日期")
    user = models.ForeignKey("core.User", on_delete=models.CASCADE, related_name="integration_deliveries", verbose_name="收件人")
    to_email = models.EmailField(blank=True, default="", verbose_name="收件邮箱")
    subject = models.CharField(max_length=255, verbose_name="邮件主题")
    status = models.CharField(max_length=16, default="pending", verbose_name="状态")  # pending|sent|failed
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")

    class Meta:
        db_table = "ir_email_delivery"
        verbose_name = "每日集成报告邮件投递"
        verbose_name_plural = verbose_name
