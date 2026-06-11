from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0008_repository_export_task"),
    ]

    operations = [
        migrations.AddField(
            model_name="compliancemissingmergescantask",
            name="scan_diagnostics",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="记录组织、分支和配对维度的取数统计，便于排查零结果任务",
                verbose_name="扫描诊断信息",
            ),
        ),
    ]
