from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class Iteration(RootModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='iterations', verbose_name="所属项目")
    name = models.CharField(max_length=255, verbose_name="迭代名称")
    code = models.CharField(max_length=255, verbose_name="迭代编号")
    start_date = models.DateField(verbose_name="开始时间")
    end_date = models.DateField(verbose_name="结束时间")
    is_current = models.BooleanField(default=False, verbose_name="是否当前迭代")
    is_healthy = models.BooleanField(default=True, verbose_name="是否健康")

    class Meta:
        db_table = 'pm_iteration'
        verbose_name = '迭代'
        verbose_name_plural = verbose_name
        
    def save(self, *args, **kwargs):
        if self.is_current:
            # Ensure only one current iteration per project
            # Exclude self.id in case of update
            qs = Iteration.objects.filter(project=self.project, is_current=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_current=False)
        super().save(*args, **kwargs)

class IterationMetric(RootModel):
    iteration = models.ForeignKey(Iteration, on_delete=models.CASCADE, related_name='metrics', verbose_name="所属迭代")
    record_date = models.DateField(verbose_name="记录日期")
    
    # Raw Data Fields
    sr_num = models.IntegerField(default=0, verbose_name="sr需求数")
    dr_num = models.IntegerField(default=0, verbose_name="dr需求数")
    ar_num = models.IntegerField(default=0, verbose_name="ar需求数")
    need_break_sr_num = models.IntegerField(default=0, verbose_name="需要分解的 sr 数")
    need_break_dr_num = models.IntegerField(default=0, verbose_name="需要分解的 dr 数")
    need_break_but_un_break_sr_num = models.IntegerField(default=0, verbose_name="需要分解但是未被分解的 sr 数")
    need_break_but_un_break_dr_num = models.IntegerField(default=0, verbose_name="需要分解但是未被分解的 dr 数")
    workload_man_dr_count = models.IntegerField(default=0, verbose_name="填写了工作量人力信息的 dr 数")
    workload_loc_dr_count = models.IntegerField(default=0, verbose_name="填写了工作量代码量的 dr 数")
    workload_man_ar_count = models.IntegerField(default=0, verbose_name="填写了工作量人力信息的 ar 数")
    workload_loc_ar_count = models.IntegerField(default=0, verbose_name="填写了工作量代码量的 ar 数")
    i_state_ar_num = models.IntegerField(default=0, verbose_name="当前置I的ar需求，Initial")
    d_state_ar_num = models.IntegerField(default=0, verbose_name="当前置I的ar需求，defined")
    p_state_ar_num = models.IntegerField(default=0, verbose_name="当前置I的ar需求，processing")
    c_state_ar_num = models.IntegerField(default=0, verbose_name="当前置I的ar需求，complete")
    a_state_ar_num = models.IntegerField(default=0, verbose_name="当前置I的ar需求，accept")
    i_state_dr_num = models.IntegerField(default=0, verbose_name="当前置I的dr需求，Initial")
    d_state_dr_num = models.IntegerField(default=0, verbose_name="当前置I的dr需求，defined")
    p_state_dr_num = models.IntegerField(default=0, verbose_name="当前置I的dr需求，processing")
    c_state_dr_num = models.IntegerField(default=0, verbose_name="当前置I的dr需求，complete")
    a_state_dr_num = models.IntegerField(default=0, verbose_name="当前置I的dr需求，accept")


    class Meta:
        db_table = 'pm_iteration_metric'
        verbose_name = '迭代指标'
        verbose_name_plural = verbose_name
        unique_together = ('iteration', 'record_date')
