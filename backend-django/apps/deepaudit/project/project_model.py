from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User

from apps.deepaudit.constants import PROJECT_MEMBER_ROLE_CHOICES, PROJECT_SOURCE_CHOICES, REPOSITORY_TYPE_CHOICES


class AuditProject(RootModel):
    name = models.CharField(max_length=255, db_index=True, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    source_type = models.CharField(max_length=20, choices=PROJECT_SOURCE_CHOICES, default='repository', verbose_name='来源类型')
    repository_url = models.CharField(max_length=1000, blank=True, null=True, verbose_name='仓库地址')
    repository_type = models.CharField(max_length=20, choices=REPOSITORY_TYPE_CHOICES, default='other', verbose_name='仓库类型')
    default_branch = models.CharField(max_length=255, default='main', verbose_name='默认分支')
    programming_languages = models.JSONField(default=list, blank=True, verbose_name='编程语言')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deepaudit_projects', db_constraint=False, verbose_name='项目拥有者')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='是否启用')

    class Meta:
        db_table = 'deepaudit_project'
        verbose_name = 'DeepAudit 项目'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['owner', 'is_deleted']),
            models.Index(fields=['source_type', 'is_deleted']),
        ]


class AuditProjectMember(RootModel):
    project = models.ForeignKey(AuditProject, on_delete=models.CASCADE, related_name='members', verbose_name='所属项目')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deepaudit_memberships', db_constraint=False, verbose_name='成员用户')
    role = models.CharField(max_length=20, choices=PROJECT_MEMBER_ROLE_CHOICES, default='member', verbose_name='项目角色')
    permissions = models.JSONField(default=dict, blank=True, verbose_name='额外权限')

    class Meta:
        db_table = 'deepaudit_project_member'
        verbose_name = 'DeepAudit 项目成员'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=['project', 'user'], name='uniq_deepaudit_project_user'),
        ]
        indexes = [
            models.Index(fields=['project', 'role']),
            models.Index(fields=['user', 'role']),
        ]
