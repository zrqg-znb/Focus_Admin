from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectConfig(models.Model):
    """项目配置信息"""
    name = models.CharField(max_length=100, verbose_name="项目名称", unique=True)
    description = models.TextField(verbose_name="项目描述", blank=True, null=True)
    
    # 配置ID字段
    codecheck_id = models.CharField(max_length=100, verbose_name="CodeCheck ID", blank=True, null=True)
    binscope_id = models.CharField(max_length=100, verbose_name="BinScope ID", blank=True, null=True)
    cooddy_id = models.CharField(max_length=100, verbose_name="Cooddy ID", blank=True, null=True)
    compiletion_check_id = models.CharField(max_length=100, verbose_name="Compilation Check ID", blank=True, null=True)
    build_check_id = models.CharField(max_length=100, verbose_name="Build Check ID", blank=True, null=True)
    build_project_id = models.CharField(max_length=100, verbose_name="Build Project ID", blank=True, null=True)
    codecov_id = models.CharField(max_length=100, verbose_name="CodeCov ID", blank=True, null=True)
    fossbot_id = models.CharField(max_length=100, verbose_name="FossBot ID", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "项目配置"
        verbose_name_plural = verbose_name
        db_table = "ci_project_config"

    def __str__(self):
        return self.name


class ProjectDailyData(models.Model):
    """项目每日数据"""
    project = models.ForeignKey(ProjectConfig, on_delete=models.CASCADE, related_name="daily_data", verbose_name="所属项目")
    date = models.DateField(verbose_name="数据日期")
    
    # 数据指标
    test_cases_count = models.IntegerField(default=0, verbose_name="测试用例数")
    test_cases_passed = models.IntegerField(default=0, verbose_name="用例通过数")
    compile_standard_options = models.JSONField(default=dict, verbose_name="编译规范选项", blank=True)
    build_standard_options = models.JSONField(default=dict, verbose_name="构建规范选项", blank=True)
    
    # 预留其他可能的字段，可以使用JSONField扩展
    extra_data = models.JSONField(default=dict, verbose_name="其他数据", blank=True)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="采集时间")

    class Meta:
        verbose_name = "项目每日数据"
        verbose_name_plural = verbose_name
        db_table = "ci_project_daily_data"
        unique_together = ('project', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.project.name} - {self.date}"


class Subscription(models.Model):
    """用户订阅信息"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions", verbose_name="订阅用户")
    project = models.ForeignKey(ProjectConfig, on_delete=models.CASCADE, related_name="subscribers", verbose_name="订阅项目")
    
    subscribed_at = models.DateTimeField(auto_now_add=True, verbose_name="订阅时间")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")

    class Meta:
        verbose_name = "用户订阅"
        verbose_name_plural = verbose_name
        db_table = "ci_subscription"
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.username} -> {self.project.name}"
