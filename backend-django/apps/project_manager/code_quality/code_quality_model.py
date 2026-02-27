from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class CodeModule(RootModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='code_modules', verbose_name="所属项目")
    oem_name = models.CharField(max_length=255, verbose_name="oem名称")
    module = models.CharField(max_length=255, verbose_name="模块名")
    owners = models.ManyToManyField('core.User', related_name='owned_code_modules', verbose_name="模块责任人")

    class Meta:
        db_table = 'pm_code_module'
        verbose_name = '代码质量模块'
        verbose_name_plural = verbose_name
        unique_together = ('project', 'oem_name', 'module')

class CodeMetric(RootModel):
    module = models.ForeignKey(CodeModule, on_delete=models.CASCADE, related_name='metrics', verbose_name="所属模块")
    record_date = models.DateField(verbose_name="记录日期")
    loc = models.IntegerField(verbose_name="代码行数")
    function_count = models.IntegerField(verbose_name="函数个数")
    dangerous_func_count = models.IntegerField(verbose_name="危险函数个数")
    duplication_rate = models.FloatField(verbose_name="重复率")
    is_clean_code = models.BooleanField(default=False, verbose_name="是否符合CleanCode标准")
    clean_code_rate = models.FloatField(default=0.0, verbose_name="CleanCode达成率")
    clean_code_total = models.IntegerField(default=11, verbose_name="CleanCode考核指标总数")
    unachieved_clean_code = models.JSONField(default=list, blank=True, verbose_name="未达标CleanCode项")
    warning_count = models.IntegerField(default=0, verbose_name="预警指标数")
    warning_metrics = models.JSONField(default=list, blank=True, verbose_name="预警指标列表")
    total_node_count = models.IntegerField(default=0, verbose_name="树节点总数")
    warning_node_count = models.IntegerField(default=0, verbose_name="预警节点数")
    version_name = models.CharField(max_length=255, blank=True, default="", verbose_name="根节点版本名")
    summary_metrics = models.JSONField(default=dict, blank=True, verbose_name="根节点指标汇总")
    raw_tree = models.JSONField(default=dict, blank=True, verbose_name="原始树数据")

    class Meta:
        db_table = 'pm_code_metric'
        verbose_name = '代码质量数据'
        verbose_name_plural = verbose_name
        unique_together = ('module', 'record_date')


class CodeMetricNode(RootModel):
    metric = models.ForeignKey(
        CodeMetric,
        on_delete=models.CASCADE,
        related_name="nodes",
        verbose_name="所属模块指标快照",
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父节点",
    )
    node_key = models.CharField(max_length=512, verbose_name="节点路径键")
    version_name = models.CharField(max_length=255, verbose_name="节点版本名")
    depth = models.IntegerField(default=0, verbose_name="树深度")
    order_index = models.IntegerField(default=0, verbose_name="同层顺序")
    metric_values = models.JSONField(default=dict, blank=True, verbose_name="节点指标值")
    warning_metrics = models.JSONField(default=list, blank=True, verbose_name="预警指标列表")
    warning_count = models.IntegerField(default=0, verbose_name="预警指标数")
    clean_code_rate = models.FloatField(default=0.0, verbose_name="CleanCode达成率")
    clean_code_total = models.IntegerField(default=11, verbose_name="CleanCode考核指标总数")
    unachieved_clean_code = models.JSONField(default=list, blank=True, verbose_name="未达标CleanCode项")
    is_clean_code = models.BooleanField(default=False, verbose_name="是否符合CleanCode标准")
    raw_payload = models.JSONField(default=dict, blank=True, verbose_name="节点原始数据")

    class Meta:
        db_table = "pm_code_metric_node"
        verbose_name = "代码质量树节点"
        verbose_name_plural = verbose_name
        unique_together = ("metric", "node_key")
        indexes = [
            models.Index(fields=["metric", "depth"], name="idx_pm_cq_node_metric_depth"),
            models.Index(fields=["metric", "parent"], name="idx_pm_cq_node_metric_parent"),
        ]


class CodeNodeOwnerConfig(RootModel):
    module = models.ForeignKey(
        CodeModule,
        on_delete=models.CASCADE,
        related_name="node_owner_configs",
        verbose_name="所属模块",
    )
    node_key = models.CharField(max_length=512, verbose_name="节点路径键")
    owners = models.ManyToManyField(
        "core.User",
        related_name="owned_code_metric_nodes",
        verbose_name="节点责任人",
    )

    class Meta:
        db_table = "pm_code_node_owner_config"
        verbose_name = "代码质量节点责任人配置"
        verbose_name_plural = verbose_name
        unique_together = ("module", "node_key")
        indexes = [
            models.Index(fields=["module"], name="idx_pm_cq_node_owner_module"),
        ]
