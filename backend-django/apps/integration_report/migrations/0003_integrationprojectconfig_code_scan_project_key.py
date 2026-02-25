from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integration_report", "0002_alter_integrationprojectconfig_project_nullable"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationprojectconfig",
            name="code_scan_project_key",
            field=models.CharField(
                blank=True,
                default="",
                max_length=128,
                verbose_name="代码扫描项目Key",
            ),
        ),
    ]
