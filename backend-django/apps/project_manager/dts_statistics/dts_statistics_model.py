from django.db import models
from django.utils import timezone

from common.fu_model import RootModel


class DtsExtension(RootModel):
    id = None

    defect_no = models.CharField(max_length=64, primary_key=True, verbose_name="DTS单号")

    # QA 识别填写
    qa_category = models.CharField(max_length=64, null=True, blank=True, verbose_name="问题大类")
    pl_group = models.ForeignKey(
        "core.PlGroup",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        db_constraint=False,
        related_name="dts_extensions",
        verbose_name="责任PL组",
    )
    is_downstream = models.CharField(max_length=8, null=True, blank=True, verbose_name="是否下游产品质量问题")
    process_quality_type = models.CharField(max_length=255, null=True, blank=True, verbose_name="产品过程质量问题分类")
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
    dev_reason = models.TextField(null=True, blank=True, verbose_name="问题原因")
    dev_intro_reason = models.TextField(null=True, blank=True, verbose_name="引入原因")
    dev_improvements = models.JSONField(default=list, blank=True, verbose_name="开发改进措施")
    dev_non_base_desc = models.JSONField(default=list, blank=True, verbose_name="非底软问题说明")
    dev_asset_link = models.CharField(max_length=512, null=True, blank=True, verbose_name="落地资产链接(开发)")
    dev_status = models.CharField(max_length=32, null=True, blank=True, verbose_name="开发改进措施状态")

    # 底软测试填写
    test_feature = models.CharField(max_length=255, null=True, blank=True, verbose_name="特效/功能")
    test_miss_reason = models.JSONField(default=list, blank=True, verbose_name="漏测原因")
    test_standard_desc = models.TextField(null=True, blank=True, verbose_name="规范问题描述")
    test_improvements = models.JSONField(default=list, blank=True, verbose_name="测试改进措施")
    test_non_test_desc = models.TextField(null=True, blank=True, verbose_name="非测试问题说明")
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
