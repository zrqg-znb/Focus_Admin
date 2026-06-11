import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0007_managed_branch_active"),
        ("core", "0009_alter_permission_code"),
    ]

    operations = [
        migrations.CreateModel(
            name="ComplianceRepositoryExportTask",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("scope", models.CharField(choices=[("all", "全量导出"), ("filtered", "按筛选导出")], db_index=True, default="all", help_text="all/filtered", max_length=16, verbose_name="导出范围")),
                ("fingerprint", models.CharField(db_index=True, max_length=64, verbose_name="任务指纹")),
                ("payload", models.JSONField(blank=True, default=dict, verbose_name="筛选条件")),
                ("status", models.CharField(choices=[("pending", "待执行"), ("running", "执行中"), ("success", "成功"), ("failed", "失败")], db_index=True, default="pending", max_length=16, verbose_name="状态")),
                ("progress", models.IntegerField(default=0, verbose_name="进度")),
                ("message", models.CharField(blank=True, default="", max_length=255, verbose_name="任务提示")),
                ("error_message", models.TextField(blank=True, default="", verbose_name="错误信息")),
                ("file_path", models.CharField(blank=True, default="", max_length=500, verbose_name="导出文件路径")),
                ("file_name", models.CharField(blank=True, default="", max_length=255, verbose_name="导出文件名")),
                ("file_size", models.BigIntegerField(default=0, verbose_name="导出文件大小")),
                ("started_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="开始时间")),
                ("finished_at", models.DateTimeField(blank=True, db_index=True, null=True, verbose_name="结束时间")),
                ("sys_creator", models.ForeignKey(blank=True, db_constraint=False, help_text="创建人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_created", to="core.user")),
                ("sys_modifier", models.ForeignKey(blank=True, db_constraint=False, help_text="修改人", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(app_label)s_%(class)s_modified", to="core.user")),
                ("user", models.ForeignKey(help_text="导出用户", on_delete=django.db.models.deletion.CASCADE, related_name="compliance_repository_export_tasks", to="core.user", verbose_name="导出用户")),
            ],
            options={
                "verbose_name": "代码库导出任务",
                "verbose_name_plural": "代码库导出任务",
                "db_table": "compliance_repository_export_task",
                "ordering": ("-sys_create_datetime",),
                "indexes": [
                    models.Index(fields=["user", "fingerprint", "status"], name="cc_repo_export_user_fp_idx"),
                    models.Index(fields=["user", "sys_create_datetime"], name="cc_repo_export_user_time_idx"),
                ],
            },
        ),
    ]
