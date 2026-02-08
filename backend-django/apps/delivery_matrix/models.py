from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class OrganizationNode(RootModel):
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name="父节点"
    )
    name = models.CharField(max_length=255, verbose_name="名称")
    code = models.CharField(max_length=100, blank=True, null=True, verbose_name="编码")
    description = models.TextField(blank=True, null=True, verbose_name="描述")
    linked_project = models.ForeignKey(
        Project,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_nodes',
        verbose_name="关联项目"
    )
    sort_order = models.IntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = 'dm_org_node'
        verbose_name = "组织节点"
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'sys_create_datetime']

class PositionStaff(RootModel):
    node = models.ForeignKey(
        OrganizationNode,
        on_delete=models.CASCADE,
        related_name='positions',
        verbose_name="所属节点"
    )
    name = models.CharField(max_length=100, verbose_name="岗位名称")
    users = models.ManyToManyField(
        'core.User',
        related_name='delivery_positions',
        verbose_name="关联人员",
        blank=True
    )

    class Meta:
        db_table = 'dm_position_staff'
        verbose_name = "岗位人员"
        verbose_name_plural = verbose_name
        unique_together = ('node', 'name')
