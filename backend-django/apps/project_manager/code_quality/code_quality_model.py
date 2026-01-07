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

    class Meta:
        db_table = 'pm_code_metric'
        verbose_name = '代码质量数据'
        verbose_name_plural = verbose_name
        unique_together = ('module', 'record_date')
