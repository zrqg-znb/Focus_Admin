from django.db import migrations, models
def backfill_cr_contribution_source(apps, schema_editor):
    """把历史贡献明细标记为 CR，并为每行生成稳定且唯一的来源标识。"""
    Record = apps.get_model("code_compliance", "ComplianceContributionRecord")
    # 不能给全部历史数据填同一个默认值；CR 原有 change_key 已经按仓库和分支唯一。
    # 极少数旧数据若缺少 change_key，则使用主键兜底，保证迁移后仍可建立唯一约束。
    for record in Record.objects.select_related("repository").all().only("id", "change_key", "repository__mode"):
        source_change_id = (record.change_key or "").strip() or f"legacy-{record.pk}"
        source_mode = getattr(record.repository, "mode", None) or "CR"
        Record.objects.filter(pk=record.pk).update(
            source_mode=source_mode,
            source_change_id=source_change_id,
        )


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
            field=models.CharField(
                blank=True,
                db_index=True,
                max_length=255,
                null=True,
                verbose_name="上游变更唯一标识",
            ),
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
        migrations.AlterField(
            model_name="compliancecontributionrecord",
            name="source_change_id",
            field=models.CharField(
                db_index=True,
                max_length=255,
                verbose_name="上游变更唯一标识",
            ),
        ),
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
