from common.fu_model import RootModel
from django.db import models
from core.user.user_model import User


COMPLIANCE_MODE_CR = "CR"
COMPLIANCE_MODE_MR = "MR"
COMPLIANCE_MODE_CHOICES = (
    (COMPLIANCE_MODE_CR, "CR"),
    (COMPLIANCE_MODE_MR, "MR"),
)

COMPLIANCE_DOMAIN_COCKPIT = "cockpit"
COMPLIANCE_DOMAIN_VEHICLE = "vehicle"
COMPLIANCE_DOMAIN_CHOICES = (
    (COMPLIANCE_DOMAIN_COCKPIT, "座舱"),
    (COMPLIANCE_DOMAIN_VEHICLE, "车控"),
)

COMPLIANCE_BRANCH_TYPE_DEVELOPMENT = "development"
COMPLIANCE_BRANCH_TYPE_TRUNK = "trunk"
COMPLIANCE_BRANCH_TYPE_RELEASE = "release"
COMPLIANCE_BRANCH_TYPE_OTHER = "other"
COMPLIANCE_BRANCH_TYPE_CHOICES = (
    (COMPLIANCE_BRANCH_TYPE_DEVELOPMENT, "开发"),
    (COMPLIANCE_BRANCH_TYPE_TRUNK, "主干"),
    (COMPLIANCE_BRANCH_TYPE_RELEASE, "发布"),
    (COMPLIANCE_BRANCH_TYPE_OTHER, "其他"),
)


class ComplianceOrganization(RootModel):
    """公司代码库系统组织主数据。"""

    group_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="组织ID",
        help_text="公司代码库系统中的组织ID",
    )
    name = models.CharField(max_length=255, verbose_name="组织名", help_text="组织名")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        db_constraint=False,
        verbose_name="父组织",
        help_text="父组织",
    )
    mode = models.CharField(
        max_length=8,
        choices=COMPLIANCE_MODE_CHOICES,
        default=COMPLIANCE_MODE_CR,
        db_index=True,
        verbose_name="模式",
        help_text="CR/MR模式",
    )
    domain = models.CharField(
        max_length=16,
        choices=COMPLIANCE_DOMAIN_CHOICES,
        default=COMPLIANCE_DOMAIN_COCKPIT,
        db_index=True,
        verbose_name="领域",
        help_text="座舱/车控",
    )
    remark = models.TextField(null=True, blank=True, verbose_name="备注", help_text="备注")

    class Meta:
        db_table = "compliance_organization"
        ordering = ("sort", "name")
        verbose_name = "代码合规组织"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["parent", "is_deleted"], name="cc_org_parent_deleted_idx"),
            models.Index(fields=["domain", "mode"], name="cc_org_domain_mode_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.group_id})"


class ComplianceRepository(RootModel):
    """公司代码库系统代码库主数据。"""

    project_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name="代码库ID",
        help_text="公司代码库系统中的代码库ID",
    )
    project_name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="代码库名",
        help_text="代码库名",
    )
    project_url = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        verbose_name="代码库URL",
        help_text="代码库URL",
    )
    organization = models.ForeignKey(
        ComplianceOrganization,
        on_delete=models.PROTECT,
        related_name="repositories",
        db_constraint=False,
        verbose_name="所属组织",
        help_text="所属组织",
    )
    mode = models.CharField(
        max_length=8,
        choices=COMPLIANCE_MODE_CHOICES,
        default=COMPLIANCE_MODE_CR,
        db_index=True,
        verbose_name="模式",
        help_text="CR/MR模式",
    )
    responsibility_groups = models.ManyToManyField(
        "core.PlGroup",
        blank=True,
        db_constraint=False,
        related_name="compliance_repositories",
        verbose_name="责任领域",
        help_text="责任PL资源组",
    )
    repo_type = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        verbose_name="代码仓类型",
        help_text="core 字典 code_compliance_repo_type 的字典项 value",
    )
    domain = models.CharField(
        max_length=16,
        choices=COMPLIANCE_DOMAIN_CHOICES,
        default=COMPLIANCE_DOMAIN_COCKPIT,
        db_index=True,
        verbose_name="领域",
        help_text="座舱/车控",
    )
    remark = models.TextField(null=True, blank=True, verbose_name="备注", help_text="备注")

    class Meta:
        db_table = "compliance_repository"
        ordering = ("project_name",)
        verbose_name = "代码合规代码库"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["organization", "is_deleted"], name="cc_repo_org_deleted_idx"),
            models.Index(fields=["domain", "mode"], name="cc_repo_domain_mode_idx"),
        ]

    def __str__(self):
        return f"{self.project_name} ({self.project_id})"


class ComplianceManagedBranch(RootModel):
    """分支主数据，区别于旧风险台账中的 ComplianceBranch。"""

    branch_name = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="分支名称",
        help_text="分支名称",
    )
    created_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="创建日期",
        help_text="创建日期",
    )
    branch_type = models.CharField(
        max_length=32,
        choices=COMPLIANCE_BRANCH_TYPE_CHOICES,
        default=COMPLIANCE_BRANCH_TYPE_OTHER,
        db_index=True,
        verbose_name="分支类型",
        help_text="开发/主干/发布/其他",
    )
    alias = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="分支别名",
        help_text="分支别名",
    )
    purpose = models.TextField(blank=True, default="", verbose_name="分支用途", help_text="分支用途")
    remark = models.TextField(null=True, blank=True, verbose_name="备注", help_text="备注")
    domain = models.CharField(
        max_length=16,
        choices=COMPLIANCE_DOMAIN_CHOICES,
        default=COMPLIANCE_DOMAIN_COCKPIT,
        db_index=True,
        verbose_name="领域",
        help_text="座舱/车控",
    )
    repositories = models.ManyToManyField(
        ComplianceRepository,
        through="ComplianceRepositoryBranch",
        related_name="managed_branches",
        blank=True,
        verbose_name="关联代码库",
    )

    class Meta:
        db_table = "compliance_managed_branch"
        ordering = ("domain", "branch_name")
        verbose_name = "代码合规分支主数据"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "branch_name"],
                name="cc_branch_domain_name_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["domain", "branch_type"], name="cc_branch_domain_type_idx"),
        ]

    def __str__(self):
        return f"{self.branch_name} ({self.domain})"


class ComplianceRepositoryBranch(RootModel):
    """代码库与分支的人工维护绑定关系。"""

    repository = models.ForeignKey(
        ComplianceRepository,
        on_delete=models.CASCADE,
        related_name="branch_links",
        db_constraint=False,
        verbose_name="代码库",
        help_text="代码库",
    )
    branch = models.ForeignKey(
        ComplianceManagedBranch,
        on_delete=models.CASCADE,
        related_name="repository_links",
        db_constraint=False,
        verbose_name="分支",
        help_text="分支",
    )

    class Meta:
        db_table = "compliance_repository_branch"
        ordering = ("repository__project_name", "branch__branch_name")
        verbose_name = "代码库分支绑定"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=["repository", "branch"],
                name="cc_repo_branch_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["repository", "is_deleted"], name="cc_rb_repo_deleted_idx"),
            models.Index(fields=["branch", "is_deleted"], name="cc_rb_branch_deleted_idx"),
        ]

class ComplianceRecord(RootModel):
    STATUS_CHOICES = (
        (0, '待处理'), # Unresolved
        (1, '无风险'), # No Risk
        (2, '已修复'), # Fixed
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='compliance_records', 
        db_constraint=False,
        help_text="关联用户"
    )
    change_id = models.CharField(max_length=255, help_text="ChangeId")
    title = models.CharField(max_length=500, blank=True, null=True, help_text="Title")
    update_time = models.DateTimeField(blank=True, null=True, help_text="UpdateTime")
    url = models.CharField(max_length=500, blank=True, null=True, help_text="URL")
    # missing_branches field is deprecated and will be removed in future migrations
    # we now use ComplianceBranch model
    
    # Status on the record can be seen as an aggregate or main status
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, help_text="状态")
    remark = models.TextField(blank=True, null=True, help_text="备注")

    class Meta:
        db_table = "compliance_record"
        ordering = ("-update_time",)
        verbose_name = "合规风险记录"
        verbose_name_plural = verbose_name

class ComplianceBranch(RootModel):
    STATUS_CHOICES = (
        (0, '待处理'), # Unresolved
        (1, '无风险'), # No Risk
        (2, '已修复'), # Fixed
    )
    
    record = models.ForeignKey(
        ComplianceRecord, 
        on_delete=models.CASCADE, 
        related_name='branches',
        db_constraint=False,
        help_text="关联的合规记录"
    )
    branch_name = models.CharField(max_length=255, help_text="分支名称")
    status = models.IntegerField(choices=STATUS_CHOICES, default=0, help_text="状态")
    remark = models.TextField(blank=True, null=True, help_text="备注")
    
    class Meta:
        db_table = "compliance_branch"
        ordering = ("branch_name",)
        verbose_name = "合规风险分支"
        verbose_name_plural = verbose_name
