from django.db import migrations, models
import django.db.models.deletion
import uuid


def copy_legacy_task_ids(apps, schema_editor):
    IntegrationProjectConfig = apps.get_model("integration_report", "IntegrationProjectConfig")
    mappings = [
        ("code_check_task_id", "code_check_task_ids"),
        ("dt_bin_task_id", "dt_bin_task_ids"),
        ("cooddy_check_task_id", "cooddy_check_task_ids"),
        ("bin_scope_task_id", "bin_scope_task_ids"),
    ]
    for config in IntegrationProjectConfig.objects.all():
        update_fields = []
        for legacy_field, list_field in mappings:
            legacy_value = (getattr(config, legacy_field, "") or "").strip()
            if legacy_value and not getattr(config, list_field, None):
                setattr(config, list_field, [legacy_value])
                update_fields.append(list_field)
        if update_fields:
            config.save(update_fields=update_fields)


class Migration(migrations.Migration):

    dependencies = [
        ("integration_report", "0006_dt_fuzz_config_and_snapshot"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationDomainDirectorySet",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("name", models.CharField(max_length=128, verbose_name="配置集名称")),
                ("description", models.TextField(blank=True, default="", verbose_name="说明")),
                ("enabled", models.BooleanField(default=True, verbose_name="是否启用")),
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
                "verbose_name": "集成报告责任田目录配置集",
                "verbose_name_plural": "集成报告责任田目录配置集",
                "db_table": "ir_domain_directory_set",
            },
        ),
        migrations.CreateModel(
            name="IntegrationDomainDirectoryRule",
            fields=[
                ("id", models.CharField(default=uuid.uuid4, editable=False, help_text="主键ID", max_length=36, primary_key=True, serialize=False)),
                ("sys_create_datetime", models.DateTimeField(auto_now_add=True, db_index=True, help_text="创建时间")),
                ("sys_update_datetime", models.DateTimeField(auto_now=True, db_index=True, help_text="更新时间")),
                ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="是否删除（软删除标识）")),
                ("sort", models.IntegerField(db_index=True, default=0, help_text="排序（数字越大越靠前）")),
                ("domain_name", models.CharField(max_length=128, verbose_name="责任田领域")),
                ("directory", models.CharField(max_length=512, verbose_name="目录字符串")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="排序")),
                ("enabled", models.BooleanField(default=True, verbose_name="是否启用")),
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
                (
                    "directory_set",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rules",
                        to="integration_report.integrationdomaindirectoryset",
                        verbose_name="配置集",
                    ),
                ),
            ],
            options={
                "verbose_name": "集成报告责任田目录规则",
                "verbose_name_plural": "集成报告责任田目录规则",
                "db_table": "ir_domain_directory_rule",
                "ordering": ("sort_order", "sys_create_datetime"),
            },
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="enable_domain_metrics",
            field=models.BooleanField(default=False, verbose_name="是否按责任田领域获取"),
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="code_check_task_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="CodeCheck任务ID列表"),
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="dt_bin_task_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="DT_Bin任务ID列表"),
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="cooddy_check_task_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="Cooddy Check任务ID列表"),
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="bin_scope_task_ids",
            field=models.JSONField(blank=True, default=list, verbose_name="Bin Scope任务ID列表"),
        ),
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="domain_directory_set",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="project_configs",
                to="integration_report.integrationdomaindirectoryset",
                verbose_name="责任田目录配置集",
            ),
        ),
        migrations.RunPython(copy_legacy_task_ids, migrations.RunPython.noop),
    ]
