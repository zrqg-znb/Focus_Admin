from django.db import models
from common.fu_model import RootModel
from apps.project_manager.project.project_model import Project

class DtsTeam(RootModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='dts_teams', verbose_name="所属项目")
    team_name = models.CharField(max_length=255, verbose_name="责任团队名称")
    parent_team = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="父责任团队")

    class Meta:
        db_table = 'pm_dts_team'
        verbose_name = '问题单责任团队'
        verbose_name_plural = verbose_name
        unique_together = ('project', 'team_name')

class DtsData(RootModel):
    team = models.ForeignKey(DtsTeam, on_delete=models.CASCADE, related_name='data', verbose_name="所属团队")
    record_date = models.DateField(verbose_name="记录日期")
    
    di = models.FloatField(verbose_name="DI值")
    target_di = models.FloatField(verbose_name="目标DI值")
    today_in_di = models.FloatField(verbose_name="今日流入DI")
    today_out_di = models.FloatField(verbose_name="今日流出DI")
    
    solve_rate = models.CharField(max_length=20, verbose_name="问题单解决率")
    critical_solve_rate = models.CharField(max_length=20, verbose_name="严重问题单解决率")
    
    suggestion_num = models.IntegerField(verbose_name="建议问题单个数")
    minor_num = models.IntegerField(verbose_name="提示单个数")
    major_num = models.IntegerField(verbose_name="严重个数")
    fatal_num = models.IntegerField(verbose_name="关键单个数")

    class Meta:
        db_table = 'pm_dts_data'
        verbose_name = '问题单数据'
        verbose_name_plural = verbose_name
        # Ensure one record per day per team
        unique_together = ('team', 'record_date')
