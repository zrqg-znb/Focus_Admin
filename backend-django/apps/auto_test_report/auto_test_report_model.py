from django.db import models

from common.fu_model import RootModel


RESULT_SUCCESS = 'success'
RESULT_FAILED = 'failed'
RESULT_TIMEOUT = 'timeout'
RESULT_SKIP = 'skip'
RESULT_CHOICES = [
    (RESULT_SUCCESS, '成功'),
    (RESULT_FAILED, '失败'),
    (RESULT_TIMEOUT, '超时'),
]


class McuPlatform(RootModel):
    name = models.CharField(max_length=128, unique=True, verbose_name='平台名称')
    version_code = models.CharField(max_length=64, unique=True, verbose_name='版本标识')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')

    class Meta:
        db_table = 'atr_mcu_platform'
        verbose_name = 'MCU平台'
        verbose_name_plural = verbose_name


class VehicleModel(RootModel):
    platform = models.ForeignKey(
        McuPlatform,
        on_delete=models.PROTECT,
        related_name='vehicles',
        verbose_name='MCU平台',
    )
    name = models.CharField(max_length=128, verbose_name='车型名称')
    vehicle_code = models.CharField(max_length=64, unique=True, verbose_name='车型编号')
    cdc_platform = models.CharField(max_length=128, verbose_name='CDC平台')
    execution_machine = models.CharField(max_length=255, verbose_name='执行机器')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    remark = models.TextField(null=True, blank=True, verbose_name='备注')

    class Meta:
        db_table = 'atr_vehicle_model'
        verbose_name = '车型'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'name'],
                name='uniq_atr_platform_vehicle_name',
            ),
        ]


class TestCase(RootModel):
    vehicle = models.ForeignKey(
        VehicleModel,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='车型',
    )
    case_no = models.CharField(max_length=128, verbose_name='用例编号')
    case_name = models.CharField(max_length=255, verbose_name='用例名称')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    class Meta:
        db_table = 'atr_test_case'
        verbose_name = '测试用例'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle', 'case_no'],
                name='uniq_atr_vehicle_case_no',
            ),
        ]


class DailyExecutionBatch(RootModel):
    vehicle = models.ForeignKey(
        VehicleModel,
        on_delete=models.CASCADE,
        related_name='daily_batches',
        verbose_name='车型',
    )
    execute_date = models.DateField(verbose_name='执行日期')
    total_count = models.IntegerField(default=0, verbose_name='总用例数')
    success_count = models.IntegerField(default=0, verbose_name='成功数')
    failed_count = models.IntegerField(default=0, verbose_name='失败数')
    timeout_count = models.IntegerField(default=0, verbose_name='超时数')
    skip_count = models.IntegerField(default=0, verbose_name='跳过数')
    total_duration_seconds = models.IntegerField(default=0, verbose_name='总时长(秒)')
    last_report_at = models.DateTimeField(null=True, blank=True, verbose_name='最近上报时间')

    class Meta:
        db_table = 'atr_daily_execution_batch'
        verbose_name = '每日执行批次'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle', 'execute_date'],
                name='uniq_atr_vehicle_execute_date',
            ),
        ]


class DailyExecutionResult(RootModel):
    vehicle = models.ForeignKey(
        VehicleModel,
        on_delete=models.CASCADE,
        related_name='daily_results',
        verbose_name='车型',
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='daily_results',
        verbose_name='测试用例',
    )
    execute_date = models.DateField(verbose_name='执行日期')
    start_time = models.DateTimeField(verbose_name='开始时间')
    duration_seconds = models.IntegerField(default=0, verbose_name='执行时长(秒)')
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, verbose_name='执行结果')
    log_url = models.CharField(max_length=1024, null=True, blank=True, verbose_name='运行日志URL')
    reported_at = models.DateTimeField(auto_now=True, verbose_name='上报时间')

    class Meta:
        db_table = 'atr_daily_execution_result'
        verbose_name = '每日执行结果'
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=['vehicle', 'execute_date', 'test_case'],
                name='uniq_atr_vehicle_date_case',
            ),
        ]
