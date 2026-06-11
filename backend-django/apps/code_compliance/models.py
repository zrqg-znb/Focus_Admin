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
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="是否活跃",
        help_text="非活跃分支视为已归档，不参与漏合扫描配对",
    )
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


MISSING_MERGE_STATUS_OPEN = "open"
MISSING_MERGE_STATUS_FIXED = "fixed"
MISSING_MERGE_STATUS_IGNORED = "ignored"
MISSING_MERGE_STATUS_CHOICES = (
    (MISSING_MERGE_STATUS_OPEN, "未处理"),
    (MISSING_MERGE_STATUS_FIXED, "已补合"),
    (MISSING_MERGE_STATUS_IGNORED, "已忽略"),
)

MISSING_MERGE_SCAN_TRIGGER_MANUAL = "manual"
MISSING_MERGE_SCAN_TRIGGER_SCHEDULED = "scheduled"
MISSING_MERGE_SCAN_TRIGGER_CHOICES = (
    (MISSING_MERGE_SCAN_TRIGGER_MANUAL, "手动"),
    (MISSING_MERGE_SCAN_TRIGGER_SCHEDULED, "定时"),
)

MISSING_MERGE_SCAN_STATUS_PENDING = "pending"
MISSING_MERGE_SCAN_STATUS_RUNNING = "running"
MISSING_MERGE_SCAN_STATUS_SUCCESS = "success"
MISSING_MERGE_SCAN_STATUS_FAILED = "failed"
MISSING_MERGE_SCAN_STATUS_CHOICES = (
    (MISSING_MERGE_SCAN_STATUS_PENDING, "待执行"),
    (MISSING_MERGE_SCAN_STATUS_RUNNING, "执行中"),
    (MISSING_MERGE_SCAN_STATUS_SUCCESS, "成功"),
    (MISSING_MERGE_SCAN_STATUS_FAILED, "失败"),
)

MISSING_MERGE_OPERATION_DETECTED = "detected"
MISSING_MERGE_OPERATION_MANUAL_HANDLE = "manual_handle"
MISSING_MERGE_OPERATION_AUTO_CLOSED = "auto_closed"
MISSING_MERGE_OPERATION_REOPENED = "reopened"
MISSING_MERGE_OPERATION_CHOICES = (
    (MISSING_MERGE_OPERATION_DETECTED, "首次自动检测"),
    (MISSING_MERGE_OPERATION_MANUAL_HANDLE, "人工处理"),
    (MISSING_MERGE_OPERATION_AUTO_CLOSED, "自动闭环"),
    (MISSING_MERGE_OPERATION_REOPENED, "重新检测为待处理"),
)

MISSING_MERGE_OPERATION_SOURCE_SYSTEM = "system"
MISSING_MERGE_OPERATION_SOURCE_MANUAL = "manual"
MISSING_MERGE_OPERATION_SOURCE_CHOICES = (
    (MISSING_MERGE_OPERATION_SOURCE_SYSTEM, "系统"),
    (MISSING_MERGE_OPERATION_SOURCE_MANUAL, "人工"),
)


class ComplianceMissingMergeRecord(RootModel):
    """自动化检测出的主干已合入但发布分支缺失的 CR 风险。"""

    organization = models.ForeignKey(
        ComplianceOrganization,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missing_merge_records",
        db_constraint=False,
        verbose_name="组织",
        help_text="识别风险时对应的组织",
    )
    repository = models.ForeignKey(
        ComplianceRepository,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missing_merge_records",
        db_constraint=False,
        verbose_name="代码库",
        help_text="识别风险时对应的代码库",
    )
    organization_group_id = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="组织ID快照",
        help_text="公司代码库系统组织ID快照",
    )
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="组织名快照",
        help_text="组织名快照",
    )
    repository_project_id = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="代码库ID快照",
        help_text="公司代码库系统代码库ID快照",
    )
    repository_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="代码库名快照",
        help_text="代码库名快照",
    )
    project_id = models.CharField(
        max_length=128,
        db_index=True,
        verbose_name="项目ID",
        help_text="数据湖查询使用的 project_id",
    )
    trunk_branch = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="主干分支",
        help_text="主干分支名称",
    )
    release_branch = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="发布分支",
        help_text="发布分支名称",
    )
    change_request_iid = models.CharField(
        max_length=128,
        blank=True,
        default="",
        verbose_name="CR内部ID",
        help_text="CR内部ID",
    )
    change_key = models.CharField(
        max_length=255,
        db_index=True,
        verbose_name="CR全局标识",
        help_text="CR全局哈希标识",
    )
    title = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="CR标题",
        help_text="CR标题",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="CR描述",
        help_text="CR描述",
    )
    web_url = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        verbose_name="CR链接",
        help_text="CR访问链接",
    )
    added_lines = models.IntegerField(default=0, verbose_name="新增行数", help_text="新增代码行数")
    removed_lines = models.IntegerField(default=0, verbose_name="删除行数", help_text="删除代码行数")
    merged_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="主干合入时间",
        help_text="CR合入主干时间",
    )
    target_branch = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="目标合入分支",
        help_text="数据湖返回的目标合入分支",
    )
    author_username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        verbose_name="创建人用户名",
        help_text="CR创建人Focus系统用户名",
    )
    author_user = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authored_missing_merge_records",
        db_constraint=False,
        verbose_name="创建人用户",
        help_text="按 CR 创建人 username 匹配到的 Focus 用户",
    )
    author_user_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="创建人姓名快照",
        help_text="识别风险时匹配到的 Focus 用户姓名快照",
    )
    author_pl_group = models.ForeignKey(
        "core.PlGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missing_merge_records",
        db_constraint=False,
        verbose_name="创建人PL组",
        help_text="按创建人所属 PL 资源组自动识别的归属",
    )
    author_pl_group_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        verbose_name="创建人PL组快照",
        help_text="创建人所属 PL 资源组名称快照；未识别时为非底软领域",
    )
    detected_at = models.DateTimeField(
        db_index=True,
        verbose_name="漏合识别时间",
        help_text="最近一次识别为漏合的时间",
    )
    status = models.CharField(
        max_length=32,
        choices=MISSING_MERGE_STATUS_CHOICES,
        default=MISSING_MERGE_STATUS_OPEN,
        db_index=True,
        verbose_name="处理状态",
        help_text="未处理/已补合/已忽略",
    )
    handled_by = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_missing_merge_records",
        db_constraint=False,
        verbose_name="处理人",
        help_text="最近一次处理人",
    )
    handled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="处理时间",
        help_text="最近一次处理时间",
    )
    handle_remark = models.TextField(
        blank=True,
        default="",
        verbose_name="处理备注",
        help_text="处理备注",
    )

    class Meta:
        db_table = "compliance_missing_merge_record"
        ordering = ("-detected_at", "-merged_at")
        verbose_name = "代码合规漏合风险"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=("repository", "trunk_branch", "release_branch", "change_key"),
                name="cc_missing_merge_record_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"], name="cc_mm_org_status_idx"),
            models.Index(fields=["repository", "status"], name="cc_mm_repo_status_idx"),
            models.Index(fields=["trunk_branch", "release_branch"], name="cc_mm_branch_pair_idx"),
            models.Index(fields=["detected_at", "status"], name="cc_mm_detect_status_idx"),
            models.Index(fields=["author_pl_group", "status"], name="cc_mm_pl_status_idx"),
        ]

    def __str__(self):
        return f"{self.repository_name}:{self.change_key}"


class ComplianceMissingMergeScanTask(RootModel):
    """漏合检测同步任务记录，用于页面展示同步结果和排障。"""

    trigger_type = models.CharField(
        max_length=32,
        choices=MISSING_MERGE_SCAN_TRIGGER_CHOICES,
        default=MISSING_MERGE_SCAN_TRIGGER_MANUAL,
        db_index=True,
        verbose_name="触发方式",
        help_text="手动/定时",
    )
    status = models.CharField(
        max_length=32,
        choices=MISSING_MERGE_SCAN_STATUS_CHOICES,
        default=MISSING_MERGE_SCAN_STATUS_PENDING,
        db_index=True,
        verbose_name="任务状态",
        help_text="待执行/执行中/成功/失败",
    )
    merged_after = models.DateTimeField(
        db_index=True,
        verbose_name="合入开始时间",
        help_text="数据湖 merged_after",
    )
    merged_before = models.DateTimeField(
        db_index=True,
        verbose_name="合入结束时间",
        help_text="数据湖 merged_before",
    )
    filter_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="筛选条件",
        help_text="手动或定时任务的组织/代码库筛选条件",
    )
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间", help_text="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="结束时间", help_text="结束时间")
    scanned_organization_count = models.IntegerField(default=0, verbose_name="扫描组织数", help_text="扫描组织数")
    scanned_repository_count = models.IntegerField(default=0, verbose_name="扫描代码库数", help_text="扫描代码库数")
    scanned_branch_pair_count = models.IntegerField(default=0, verbose_name="扫描分支对数", help_text="扫描分支对数")
    detected_count = models.IntegerField(default=0, verbose_name="识别风险数", help_text="本次识别漏合风险数")
    created_count = models.IntegerField(default=0, verbose_name="新增风险数", help_text="本次新增风险数")
    updated_count = models.IntegerField(default=0, verbose_name="更新风险数", help_text="本次更新风险数")
    fixed_count = models.IntegerField(default=0, verbose_name="自动补合数", help_text="本次自动标记已补合数量")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息", help_text="失败错误信息")

    class Meta:
        db_table = "compliance_missing_merge_scan_task"
        ordering = ("-sys_create_datetime",)
        verbose_name = "代码合规漏合检测任务"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["status", "trigger_type"], name="cc_mm_task_status_trigger_idx"),
            models.Index(fields=["merged_after", "merged_before"], name="cc_mm_task_time_idx"),
        ]

    def __str__(self):
        return f"{self.trigger_type}:{self.status}:{self.merged_after}"


class ComplianceMissingMergeOperationLog(RootModel):
    """漏合风险操作历史台账，用于追溯自动检测、人工处理和自动闭环。"""

    record = models.ForeignKey(
        ComplianceMissingMergeRecord,
        on_delete=models.CASCADE,
        related_name="operation_logs",
        db_constraint=False,
        verbose_name="漏合风险",
        help_text="关联漏合风险记录",
    )
    scan_task = models.ForeignKey(
        ComplianceMissingMergeScanTask,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="operation_logs",
        db_constraint=False,
        verbose_name="扫描任务",
        help_text="触发本次系统操作的扫描任务",
    )
    operation_type = models.CharField(
        max_length=32,
        choices=MISSING_MERGE_OPERATION_CHOICES,
        db_index=True,
        verbose_name="操作类型",
        help_text="首次自动检测/人工处理/自动闭环/重新检测",
    )
    source = models.CharField(
        max_length=16,
        choices=MISSING_MERGE_OPERATION_SOURCE_CHOICES,
        default=MISSING_MERGE_OPERATION_SOURCE_SYSTEM,
        db_index=True,
        verbose_name="操作来源",
        help_text="系统/人工",
    )
    from_status = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="变更前状态",
        help_text="操作前处理状态",
    )
    to_status = models.CharField(
        max_length=32,
        blank=True,
        default="",
        verbose_name="变更后状态",
        help_text="操作后处理状态",
    )
    operator = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="missing_merge_operation_logs",
        db_constraint=False,
        verbose_name="操作人",
        help_text="人工操作人；系统操作为空",
    )
    operator_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="操作人快照",
        help_text="操作发生时的人名快照",
    )
    remark = models.TextField(
        blank=True,
        default="",
        verbose_name="操作备注",
        help_text="系统自动备注或人工填写备注",
    )
    operated_at = models.DateTimeField(
        db_index=True,
        verbose_name="操作时间",
        help_text="操作发生时间",
    )

    class Meta:
        db_table = "compliance_missing_merge_operation_log"
        ordering = ("-operated_at", "-sys_create_datetime")
        verbose_name = "代码合规漏合风险操作历史"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["record", "operated_at"], name="cc_mm_log_record_time_idx"),
            models.Index(fields=["operation_type", "source"], name="cc_mm_log_type_source_idx"),
        ]

    def __str__(self):
        return f"{self.record_id}:{self.operation_type}:{self.operated_at}"


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
