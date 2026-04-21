from django.db import models
from django.utils import timezone

from common.fu_model import RootModel


class DtsExtension(RootModel):
    id = None

    defect_no = models.CharField(max_length=64, primary_key=True, verbose_name="DTS单号")

    # QA 识别填写
    is_downstream = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否下游产品质量问题")
    process_quality_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="产品过程质量问题分类")
    issue_intro_stage = models.CharField(max_length=255, null=True, blank=True, verbose_name="问题引入阶段")
    need_aar = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否需要AAR")
    need_dev_analyze = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否需要开发分析引入原因")
    need_test_analyze = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否需要测试分析漏测")
    dev_owner = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="dts_dev_extensions",
        verbose_name="开发责任人",
    )
    test_owner = models.ForeignKey(
        "core.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="dts_test_extensions",
        verbose_name="测试责任人",
    )
    is_dev_analyzed = models.CharField(max_length=8, null=True, blank=True, verbose_name="开发分析是否完成")
    is_test_analyzed = models.CharField(max_length=8, null=True, blank=True, verbose_name="测试分析是否完成")
    qa_remark = models.TextField(null=True, blank=True, verbose_name="备注")

    # 底软开发填写
    dev_sub_category = models.JSONField(default=list, blank=True, verbose_name="问题小类")
    dev_feature = models.CharField(max_length=255, null=True, blank=True, verbose_name="特性/功能")
    dev_reason = models.TextField(null=True, blank=True, verbose_name="问题原因")
    dev_intro_reason = models.TextField(null=True, blank=True, verbose_name="引入原因")
    dev_issue_intro_point = models.CharField(max_length=255, null=True, blank=True, verbose_name="问题引入点")
    dev_issue_probability = models.CharField(max_length=255, null=True, blank=True, verbose_name="问题概率")
    dev_common_issue_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="是否共性问题")
    is_base_soft_issue = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否底软问题")
    is_duplicate_issue = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否重复问题")
    duplicate_issue_no = models.CharField(max_length=64, null=True, blank=True, verbose_name="重复问题单号")
    dev_control_points = models.JSONField(default=list, blank=True, verbose_name="需要补强的开发控制点")
    dev_intro_point_analysis = models.TextField(null=True, blank=True, verbose_name="引入点分析")
    dev_improvements = models.JSONField(default=list, blank=True, verbose_name="开发改进措施")
    dev_non_base_desc = models.JSONField(default=list, blank=True, verbose_name="非底软问题说明")
    dev_remark = models.TextField(null=True, blank=True, verbose_name="开发备注")
    dev_aar_link = models.CharField(max_length=512, null=True, blank=True, verbose_name="AAR链接")
    dev_asset_link = models.CharField(max_length=512, null=True, blank=True, verbose_name="落地资产链接(开发)")
    dev_asset_type = models.JSONField(default=list, blank=True, verbose_name="落地资产类型(开发)")
    dev_status = models.CharField(max_length=32, null=True, blank=True, verbose_name="开发改进措施状态")

    # 底软测试填写
    test_miss_reason = models.JSONField(default=list, blank=True, verbose_name="漏测原因")
    test_standard_desc = models.TextField(null=True, blank=True, verbose_name="规范问题描述")
    test_improvements = models.JSONField(default=list, blank=True, verbose_name="测试改进措施")
    test_non_test_desc = models.TextField(null=True, blank=True, verbose_name="非测试问题说明")
    test_remark = models.TextField(null=True, blank=True, verbose_name="测试备注")
    test_asset_link = models.CharField(max_length=512, null=True, blank=True, verbose_name="落地资产链接(测试)")
    test_status = models.CharField(max_length=32, null=True, blank=True, verbose_name="漏测改进措施状态")

    class Meta:
        db_table = "pm_dts_extension"
        verbose_name = "DTS拓展数据"
        verbose_name_plural = verbose_name


class DtsDefectProjectLink(RootModel):
    defect_no = models.CharField(max_length=64, verbose_name="DTS单号", db_index=True)
    project = models.ForeignKey(
        "project_manager.Project",
        on_delete=models.CASCADE,
        related_name="dts_defect_links",
        verbose_name="项目",
    )
    team_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="命中团队")
    version_c = models.CharField(max_length=255, null=True, blank=True, verbose_name="命中版本")
    last_seen_at = models.DateTimeField(default=timezone.now, verbose_name="最近命中时间")

    class Meta:
        db_table = "pm_dts_defect_project_link"
        verbose_name = "DTS问题单项目关联"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["defect_no", "project"],
                name="uniq_pm_dts_defect_project",
            )
        ]
        indexes = [
            models.Index(fields=["defect_no"]),
            models.Index(fields=["project", "last_seen_at"]),
        ]


class DtsStatisticsQueryTask(RootModel):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
    )

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="dts_statistics_query_tasks",
        verbose_name="用户",
    )
    fingerprint = models.CharField(max_length=64, db_index=True, verbose_name="查询指纹")
    payload = models.JSONField(default=dict, blank=True, verbose_name="筛选条件")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="状态",
    )
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="任务提示")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    progress = models.IntegerField(default=0, verbose_name="进度")
    scanned_pages = models.IntegerField(default=0, verbose_name="已扫描页数")
    total_pages = models.IntegerField(default=0, verbose_name="总页数")
    matched_count = models.IntegerField(default=0, verbose_name="匹配问题单数")
    result_cache_key = models.CharField(max_length=255, blank=True, default="", verbose_name="结果缓存键")
    started_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="结束时间")

    class Meta:
        db_table = "pm_dts_statistics_query_task"
        verbose_name = "DTS统计查询准备任务"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["user", "fingerprint", "status"]),
            models.Index(fields=["user", "sys_create_datetime"]),
        ]


class DtsStatisticsExportTask(RootModel):
    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
    )

    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="dts_statistics_export_tasks",
        verbose_name="用户",
    )
    fingerprint = models.CharField(max_length=64, db_index=True, verbose_name="导出指纹")
    payload = models.JSONField(default=dict, blank=True, verbose_name="筛选条件")
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="状态",
    )
    message = models.CharField(max_length=255, blank=True, default="", verbose_name="任务提示")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    progress = models.IntegerField(default=0, verbose_name="进度")
    file_path = models.CharField(max_length=500, blank=True, default="", verbose_name="导出文件路径")
    file_name = models.CharField(max_length=255, blank=True, default="", verbose_name="导出文件名")
    file_size = models.BigIntegerField(default=0, verbose_name="导出文件大小(字节)")
    started_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="结束时间")

    class Meta:
        db_table = "pm_dts_statistics_export_task"
        verbose_name = "DTS统计导出任务"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["user", "fingerprint", "status"]),
            models.Index(fields=["user", "sys_create_datetime"]),
        ]
