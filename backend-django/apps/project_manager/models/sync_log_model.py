from django.db import models
from common.fu_model import RootModel

class SyncLog(RootModel):
    """
    同步日志模型
    记录各个模块的数据同步操作日志
    """
    
    SYNC_TYPE_CHOICES = [
        ('iteration', '迭代数据'),
        ('dts', 'DTS问题单'),
        ('code_quality', '代码质量'),
        ('milestone', '里程碑'),
        ('project', '项目信息'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '进行中'),
        ('success', '成功'),
        ('failed', '失败'),
    ]
    
    project_id = models.CharField(max_length=64, verbose_name="项目ID", db_index=True)
    sync_type = models.CharField(max_length=32, choices=SYNC_TYPE_CHOICES, verbose_name="同步类型")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    
    # 执行结果摘要
    result_summary = models.TextField(blank=True, null=True, verbose_name="结果摘要")
    # 详细日志/错误信息
    detail_log = models.TextField(blank=True, null=True, verbose_name="详细日志")
    
    # 耗时（秒）
    duration = models.FloatField(default=0.0, verbose_name="耗时(秒)")
    
    class Meta:
        db_table = "pm_sync_log"
        verbose_name = "同步日志"
        verbose_name_plural = verbose_name
        ordering = ['-sys_create_datetime']
