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
    req_decomposition_rate = models.FloatField(verbose_name="需求分解率")
    req_drift_rate = models.FloatField(verbose_name="需求游离率")
    req_completion_rate = models.FloatField(verbose_name="需求完成率")
    req_workload = models.FloatField(verbose_name="需求工作量")
    completed_workload = models.FloatField(verbose_name="已完成工作量")

    class Meta:
        db_table = 'pm_iteration_metric'
        verbose_name = '迭代指标'
        verbose_name_plural = verbose_name
        unique_together = ('iteration', 'record_date')
