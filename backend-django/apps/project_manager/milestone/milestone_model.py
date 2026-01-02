from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class Milestone(RootModel):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='milestone', verbose_name="所属项目")
    qg1_date = models.DateField(null=True, blank=True, verbose_name="QG1时间")
    qg2_date = models.DateField(null=True, blank=True, verbose_name="QG2时间")
    qg3_date = models.DateField(null=True, blank=True, verbose_name="QG3时间")
    qg4_date = models.DateField(null=True, blank=True, verbose_name="QG4时间")
    qg5_date = models.DateField(null=True, blank=True, verbose_name="QG5时间")
    qg6_date = models.DateField(null=True, blank=True, verbose_name="QG6时间")
    qg7_date = models.DateField(null=True, blank=True, verbose_name="QG7时间")
    qg8_date = models.DateField(null=True, blank=True, verbose_name="QG8时间")

    class Meta:
        db_table = 'pm_milestone'
        verbose_name = '里程碑'
        verbose_name_plural = verbose_name
