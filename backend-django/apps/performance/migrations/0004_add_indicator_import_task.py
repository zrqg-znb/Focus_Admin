import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0006_alter_user_manager"),
        ("performance", "0003_add_performanceindicator_category"),
    ]

    operations = [
        migrations.CreateModel(
            name="PerformanceIndicatorImportTask",
            fields=[
                (
                    "id",
                    models.CharField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="主键ID",
                        max_length=36,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "sys_create_datetime",
                    models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间"),
                ),
                (
                    "sys_update_datetime",
                    models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间"),
                ),
                (
                    "is_deleted",
                    models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）"),
                ),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "等待中"), ("running", "执行中"), ("success", "成功"), ("failed", "失败")],
                        default="pending",
                        help_text="状态",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                ("progress", models.IntegerField(default=0, help_text="进度(0-100)", verbose_name="进度")),
                ("filename", models.CharField(help_text="文件名", max_length=255, verbose_name="文件名")),
                ("file_path", models.CharField(help_text="文件路径", max_length=500, verbose_name="文件路径")),
                ("total_rows", models.IntegerField(blank=True, help_text="总行数", null=True, verbose_name="总行数")),
                ("processed_rows", models.IntegerField(default=0, help_text="已处理行数", verbose_name="已处理行数")),
                ("success_count", models.IntegerField(default=0, help_text="成功数", verbose_name="成功数")),
                ("error_count", models.IntegerField(default=0, help_text="失败数", verbose_name="失败数")),
                ("message", models.CharField(blank=True, default="", help_text="消息", max_length=500, verbose_name="消息")),
                ("errors", models.TextField(blank=True, default="", help_text="错误详情(截断)", verbose_name="错误详情")),
                ("started_at", models.DateTimeField(blank=True, help_text="开始时间", null=True, verbose_name="开始时间")),
                ("finished_at", models.DateTimeField(blank=True, help_text="结束时间", null=True, verbose_name="结束时间")),
                (
                    "sys_creator",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="创建人",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="core.user",
                    ),
                ),
                (
                    "sys_modifier",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        help_text="修改人",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_modified",
                        to="core.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "指标定义导入任务",
                "verbose_name_plural": "指标定义导入任务",
                "db_table": "performance_indicator_import_task",
                "ordering": ["-sys_create_datetime"],
            },
        ),
    ]
