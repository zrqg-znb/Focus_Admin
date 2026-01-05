from django.db import models
from common.fu_model import RootModel

class Project(RootModel):
    name = models.CharField(max_length=255, verbose_name="项目名")
    domain = models.CharField(max_length=255, verbose_name="项目领域")
    type = models.CharField(max_length=255, verbose_name="项目类型")
    code = models.CharField(max_length=255, unique=True, verbose_name="项目编码")
    managers = models.ManyToManyField('core.User', related_name='managed_projects', verbose_name="项目经理")
    is_closed = models.BooleanField(default=False, verbose_name="是否结项")
    repo_url = models.CharField(max_length=512, blank=True, null=True, verbose_name="制品仓号/地址")
    remark = models.TextField(blank=True, null=True, verbose_name="备注")
    
    # Switches
    enable_milestone = models.BooleanField(default=True, verbose_name="是否统计里程碑")
    enable_iteration = models.BooleanField(default=True, verbose_name="是否统计迭代数据")
    design_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="迭代中台配置 id")
    sub_teams = models.JSONField(default=list, null=True, blank=True, verbose_name="迭代责任团队")
    enable_quality = models.BooleanField(default=True, verbose_name="是否统计代码质量")

    class Meta:
        db_table = 'pm_project'
        verbose_name = '项目管理'
        verbose_name_plural = verbose_name
