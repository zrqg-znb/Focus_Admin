from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class DeliveryDomain(RootModel):
    name = models.CharField(max_length=255, verbose_name="领域名称")
    code = models.CharField(max_length=255, unique=True, verbose_name="领域编码")
    interface_people = models.ManyToManyField('core.User', related_name='delivery_domains', verbose_name="领域接口人", blank=True)
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        db_table = 'dm_delivery_domain'
        verbose_name = '交付领域'
        verbose_name_plural = verbose_name

class ProjectGroup(RootModel):
    name = models.CharField(max_length=255, verbose_name="项目群名称")
    domain = models.ForeignKey(DeliveryDomain, on_delete=models.CASCADE, related_name='groups', verbose_name="所属领域")
    managers = models.ManyToManyField('core.User', related_name='delivery_project_groups', verbose_name="项目群经理", blank=True)
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        db_table = 'dm_project_group'
        verbose_name = '项目群'
        verbose_name_plural = verbose_name

class ProjectComponent(RootModel):
    name = models.CharField(max_length=255, verbose_name="组件名称")
    group = models.ForeignKey(ProjectGroup, on_delete=models.CASCADE, related_name='components', verbose_name="所属项目群")
    managers = models.ManyToManyField('core.User', related_name='delivery_components', verbose_name="项目经理", blank=True)
    linked_project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='delivery_component', verbose_name="关联项目")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")

    class Meta:
        db_table = 'dm_project_component'
        verbose_name = '项目组件'
        verbose_name_plural = verbose_name
