# Generated manually for code compliance branch archival state.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("code_compliance", "0006_missing_merge_author_pl_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="compliancemanagedbranch",
            name="is_active",
            field=models.BooleanField(
                db_index=True,
                default=True,
                help_text="非活跃分支视为已归档，不参与漏合扫描配对",
                verbose_name="是否活跃",
            ),
        ),
    ]
