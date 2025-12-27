from django.db import models
from common.fu_model import RootModel
from core.user.user_model import User

class PerformanceIndicator(RootModel):
    code = models.CharField(max_length=100, unique=True, null=True, blank=True, verbose_name="业务唯一标识", help_text="业务唯一标识")
    name = models.CharField(max_length=255, verbose_name="指标名称", help_text="指标名称")
    module = models.CharField(max_length=100, verbose_name="所属模块", help_text="所属模块")
    project = models.CharField(max_length=100, verbose_name="所属项目", help_text="所属项目")
    chip_type = models.CharField(max_length=100, verbose_name="芯片类型", help_text="芯片类型")
    
    VALUE_TYPE_CHOICES = (
        ('avg', '平均值'),
        ('min', '最小值'),
        ('max', '最大值'),
    )
    value_type = models.CharField(max_length=20, choices=VALUE_TYPE_CHOICES, default='avg', verbose_name="值类型", help_text="值类型")
    
    baseline_value = models.FloatField(verbose_name="基线值", help_text="基线值")
    baseline_unit = models.CharField(max_length=50, verbose_name="单位", help_text="单位")
    fluctuation_range = models.FloatField(verbose_name="允许浮动范围", help_text="允许浮动范围")
    
    DIRECTION_CHOICES = (
        ('up', '越大越好'),
        ('down', '越小越好'),
        ('none', '无方向'),
    )
    fluctuation_direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='none', verbose_name="浮动方向", help_text="浮动方向")
    
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="责任人", help_text="责任人", related_name="performance_indicators")

    class Meta:
        db_table = 'performance_indicator'
        verbose_name = '性能指标'
        verbose_name_plural = verbose_name
        unique_together = ('project', 'module', 'chip_type', 'name')
        ordering = ['-sys_create_datetime']

class PerformanceIndicatorData(RootModel):
    indicator = models.ForeignKey(PerformanceIndicator, on_delete=models.CASCADE, related_name='data', verbose_name="指标", help_text="指标")
    date = models.DateField(verbose_name="测试日期", help_text="测试日期")
    value = models.FloatField(verbose_name="具体测试值", help_text="具体测试值")
    fluctuation_value = models.FloatField(verbose_name="浮动差值", help_text="浮动差值")

    class Meta:
        db_table = 'performance_indicator_data'
        verbose_name = '性能数据'
        verbose_name_plural = verbose_name
        unique_together = ('indicator', 'date')
        ordering = ['-date']
