from django.db import models

from common.fu_model import RootModel
from core.user.user_model import User


class TestEnvironment(RootModel):
    DOMAIN_CHOICES = (
        ('cockpit', '座舱'),
        ('vehicle', '车控'),
    )
    CATEGORY_CHOICES = (
        ('dev', '开发'),
        ('test', '测试'),
        ('ci', 'CI'),
    )
    STATUS_CHOICES = (
        ('idle', '空闲'),
        ('occupied', '占用中'),
    )

    ip_address = models.GenericIPAddressField(verbose_name='IP地址', help_text='远程环境 IP 地址')
    account = models.CharField(max_length=100, blank=True, default='', verbose_name='账号')
    password_encrypted = models.TextField(blank=True, default='', verbose_name='加密密码')
    domain = models.CharField(max_length=20, choices=DOMAIN_CHOICES, default='cockpit', db_index=True, verbose_name='领域')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='test', db_index=True, verbose_name='环境分类')
    project_name = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name='项目名称')
    vehicle_model = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name='车型')
    device_material = models.CharField(max_length=100, blank=True, default='', verbose_name='测试设备物料')
    asset_number = models.CharField(max_length=100, blank=True, default='', verbose_name='资产编号')
    config = models.JSONField(default=dict, blank=True, verbose_name='配置情况')
    shelf_location = models.CharField(max_length=200, blank=True, default='', verbose_name='货架位置')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='idle', db_index=True, verbose_name='状态')
    current_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='occupied_test_environments',
        verbose_name='当前占用人',
    )
    occupied_at = models.DateTimeField(null=True, blank=True, verbose_name='占用开始时间')

    class Meta:
        db_table = 'environment_management_environment'
        verbose_name = '测试环境'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['domain', 'category']),
            models.Index(fields=['status', 'current_user']),
            models.Index(fields=['project_name', 'vehicle_model']),
        ]
        ordering = ['is_deleted', '-sort', 'ip_address']

    def __str__(self):
        return f'{self.ip_address} {self.project_name}'.strip()


class EnvironmentFavorite(RootModel):
    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, related_name='favorites', verbose_name='环境')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='environment_favorites', verbose_name='用户')

    class Meta:
        db_table = 'environment_management_favorite'
        verbose_name = '环境收藏'
        verbose_name_plural = verbose_name
        unique_together = ('environment', 'user')
        indexes = [models.Index(fields=['user', 'environment'])]


class EnvironmentQueue(RootModel):
    QUEUE_TYPE_CHOICES = (
        ('normal', '排队'),
        ('jump', '插队'),
    )
    STATUS_CHOICES = (
        ('waiting', '等待中'),
        ('cancelled', '已取消'),
        ('done', '已完成'),
    )

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, related_name='queues', verbose_name='环境')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='environment_queues', verbose_name='用户')
    queue_type = models.CharField(max_length=20, choices=QUEUE_TYPE_CHOICES, default='normal', verbose_name='队列类型')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', db_index=True, verbose_name='状态')
    position = models.IntegerField(default=0, db_index=True, verbose_name='排序位置')
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='申请时间')

    class Meta:
        db_table = 'environment_management_queue'
        verbose_name = '环境队列'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['environment', 'status', 'position']),
            models.Index(fields=['environment', 'user', 'status']),
        ]
        ordering = ['position', 'requested_at']


class EnvironmentRecord(RootModel):
    ACTION_CHOICES = (
        ('occupy', '占用'),
        ('release', '释放'),
        ('queue', '排队'),
        ('cancel_queue', '取消排队'),
        ('jump_queue', '插队'),
        ('admin_update', '管理员更新'),
    )

    environment = models.ForeignKey(TestEnvironment, on_delete=models.CASCADE, related_name='records', verbose_name='环境')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='environment_records', verbose_name='操作人')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True, verbose_name='动作')
    message = models.CharField(max_length=500, blank=True, default='', verbose_name='说明')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='占用开始时间')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='占用结束时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='持续时长')
    snapshot = models.JSONField(default=dict, blank=True, verbose_name='快照')

    class Meta:
        db_table = 'environment_management_record'
        verbose_name = '环境操作记录'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['environment', '-sys_create_datetime']),
            models.Index(fields=['operator', '-sys_create_datetime']),
        ]
        ordering = ['-sys_create_datetime']
