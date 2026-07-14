from django.db import migrations, models
from django.db.models import F


def backfill_cr_contribution_source(apps, schema_editor):
    """把历史贡献明细标记为 CR，并以原 change_key 作为上游幂等标识。"""
    Record = apps.get_model("code_compliance", "ComplianceContributionRecord")
    Record.objects.filter(source_change_id="").update(source_change_id=F("change_key"))


class Migration(migrations.Migration):
    dependencies = [("code_compliance", "0011_contribution_code_baseline")]

    operations = [
        migrations.AddField(
            model_name="compliancecontributionrecord",
            name="source_mode",
            field=models.CharField(
                choices=[("CR", "CR"), ("MR", "MR")],
                db_index=True,
                default="CR",
                help_text="CR/MR 数据湖来源快照",
                max_length=8,
                verbose_name="数据来源模式",
            ),
        ),
        migrations.AddField(
            model_name="compliancecontributionrecord",
            name="source_change_id",
            field=models.CharField(db_index=True, default="", max_length=255, verbose_name="上游变更唯一标识"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="compliancecontributiondailyaggregate",
            name="source_mode",
            field=models.CharField(
                choices=[("CR", "CR"), ("MR", "MR")],
                db_index=True,
                default="CR",
                max_length=8,
                verbose_name="数据来源模式",
            ),
        ),
        migrations.AlterField(
            model_name="compliancecontributionrecord",
            name="change_key",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255, verbose_name="CR全局标识"),
        ),
        migrations.RunPython(backfill_cr_contribution_source, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="compliancecontributionrecord",
            name="cc_contribution_record_uniq",
        ),
        migrations.AddConstraint(
            model_name="compliancecontributionrecord",
            constraint=models.UniqueConstraint(
                fields=("repository", "branch_name", "source_mode", "source_change_id"),
                name="cc_contribution_record_source_uniq",
            ),
        ),
        migrations.AddIndex(
            model_name="compliancecontributionrecord",
            index=models.Index(fields=["source_mode", "contribution_date"], name="cc_ctr_mode_day_idx"),
        ),
    ]
