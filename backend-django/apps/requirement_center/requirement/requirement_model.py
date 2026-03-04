from django.db import models

from common.fu_model import RootModel


class RequirementStatus:
    DRAFT = "draft"
    SUBMITTED = "submitted"
    NEED_INFO = "need_info"
    ACCEPTED = "accepted"
    PLANNED = "planned"
    IN_DEV = "in_dev"
    IN_ACCEPTANCE = "in_acceptance"
    DONE = "done"
    REJECTED = "rejected"
    ARCHIVED = "archived"

    CHOICES = [
        (DRAFT, "草稿"),
        (SUBMITTED, "待评审"),
        (NEED_INFO, "待补充"),
        (ACCEPTED, "已接纳"),
        (PLANNED, "已排期"),
        (IN_DEV, "开发中"),
        (IN_ACCEPTANCE, "待验收"),
        (DONE, "已完成"),
        (REJECTED, "已拒绝"),
        (ARCHIVED, "已归档"),
    ]

    REVIEW_PENDING = {SUBMITTED}
    DEV_PENDING = {PLANNED, IN_DEV, IN_ACCEPTANCE}
    CLOSED = {DONE, REJECTED, ARCHIVED}


class RequirementAction:
    CREATE = "create"
    UPDATE = "update"
    SUBMIT = "submit"
    REVIEW = "review"
    TRANSFER_REVIEWER = "transfer_reviewer"
    ASSIGN_OWNER = "assign_owner"
    TRANSITION = "transition"
    COMMENT = "comment"
    BATCH_ASSIGN_REVIEWER = "batch_assign_reviewer"
    BATCH_ASSIGN_OWNER = "batch_assign_owner"
    BATCH_PRIORITY = "batch_priority"
    BATCH_ARCHIVE = "batch_archive"
    SPLIT_CHILD = "split_child"


class Requirement(RootModel):
    title = models.CharField(max_length=255, db_index=True, verbose_name="需求标题")
    description = models.TextField(blank=True, default="", verbose_name="需求描述")
    business_value = models.TextField(blank=True, default="", verbose_name="业务价值")
    acceptance_criteria = models.TextField(
        blank=True,
        default="",
        verbose_name="验收标准",
    )

    type = models.CharField(max_length=64, default="", db_index=True, verbose_name="需求类型")
    source = models.CharField(max_length=64, default="", db_index=True, verbose_name="需求来源")
    priority = models.CharField(max_length=32, default="medium", db_index=True, verbose_name="优先级")
    status = models.CharField(
        max_length=32,
        choices=RequirementStatus.CHOICES,
        default=RequirementStatus.DRAFT,
        db_index=True,
        verbose_name="状态",
    )

    submitter = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_requirements",
        verbose_name="提单人",
    )
    reviewer = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewing_requirements",
        verbose_name="评审人",
    )
    owner = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_requirements",
        verbose_name="责任人",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        verbose_name="父需求",
    )

    root_id = models.CharField(max_length=36, default="", db_index=True, verbose_name="根需求ID")
    level = models.PositiveIntegerField(default=0, verbose_name="树层级")
    tree_path = models.CharField(max_length=700, default="", db_index=True, verbose_name="树路径")
    child_count = models.PositiveIntegerField(default=0, verbose_name="直接子需求数量")
    is_leaf = models.BooleanField(default=True, db_index=True, verbose_name="是否叶子节点")

    attachments = models.JSONField(default=list, blank=True, verbose_name="附件文件ID列表")

    review_due_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="评审截止时间")
    dev_due_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name="开发截止时间")
    is_review_overdue = models.BooleanField(default=False, db_index=True, verbose_name="评审是否超时")
    is_dev_overdue = models.BooleanField(default=False, db_index=True, verbose_name="开发是否超时")

    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name="提交时间")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="接纳时间")
    planned_at = models.DateTimeField(null=True, blank=True, verbose_name="排期时间")
    dev_started_at = models.DateTimeField(null=True, blank=True, verbose_name="开发开始时间")
    done_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = "rc_requirement"
        verbose_name = "需求单"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["parent", "sort"], name="idx_rc_req_parent_sort"),
            models.Index(fields=["root_id", "tree_path"], name="idx_rc_req_root_path"),
            models.Index(fields=["is_leaf", "status"], name="idx_rc_req_leaf_status"),
            models.Index(fields=["status", "priority", "sys_create_datetime"], name="idx_rc_req_status_pri_ct"),
            models.Index(fields=["reviewer", "status"], name="idx_rc_req_reviewer_status"),
            models.Index(fields=["owner", "status"], name="idx_rc_req_owner_status"),
            models.Index(fields=["is_review_overdue", "is_dev_overdue"], name="idx_rc_req_overdue"),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(parent__isnull=True) | ~models.Q(id=models.F("parent_id")),
                name="ck_rc_req_parent_not_self",
            ),
        ]


class RequirementComment(RootModel):
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="所属需求",
    )
    commenter = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requirement_comments",
        verbose_name="评论人",
    )
    content = models.TextField(verbose_name="评论内容")
    mentions = models.JSONField(default=list, blank=True, verbose_name="@用户ID列表")

    class Meta:
        db_table = "rc_requirement_comment"
        verbose_name = "需求评论"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["requirement", "sys_create_datetime"], name="idx_rc_req_comment_req_time"),
        ]


class RequirementLog(RootModel):
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="logs",
        verbose_name="所属需求",
    )
    action = models.CharField(max_length=64, db_index=True, verbose_name="操作动作")
    from_status = models.CharField(max_length=32, blank=True, default="", verbose_name="变更前状态")
    to_status = models.CharField(max_length=32, blank=True, default="", verbose_name="变更后状态")
    operator = models.ForeignKey(
        "core.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requirement_logs",
        verbose_name="操作人",
    )
    note = models.TextField(blank=True, default="", verbose_name="备注")

    class Meta:
        db_table = "rc_requirement_log"
        verbose_name = "需求日志"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["requirement", "sys_create_datetime"], name="idx_rc_req_log_req_time"),
            models.Index(fields=["action", "sys_create_datetime"], name="idx_rc_req_log_action_time"),
        ]


class RequirementWatcher(RootModel):
    requirement = models.ForeignKey(
        Requirement,
        on_delete=models.CASCADE,
        related_name="watchers",
        verbose_name="所属需求",
    )
    user = models.ForeignKey(
        "core.User",
        on_delete=models.CASCADE,
        related_name="watching_requirements",
        verbose_name="关注用户",
    )

    class Meta:
        db_table = "rc_requirement_watcher"
        verbose_name = "需求关注人"
        verbose_name_plural = verbose_name
        unique_together = [("requirement", "user")]
        indexes = [
            models.Index(fields=["user", "sys_create_datetime"], name="idx_rc_req_watch_user_time"),
        ]
