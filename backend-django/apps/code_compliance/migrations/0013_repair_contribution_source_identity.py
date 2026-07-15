from django.db import migrations


def repair_contribution_source_identity(apps, schema_editor):
    """修复旧版 0012 部分执行或错误默认值造成的来源 ID 冲突。"""
    connection = schema_editor.connection
    Record = apps.get_model("code_compliance", "ComplianceContributionRecord")
    table = Record._meta.db_table
    quote = connection.ops.quote_name

    # 兼容 0012 在 MySQL 上留下字段但未完成迁移记录的情况。
    columns = {item.name for item in connection.introspection.get_table_description(connection.cursor(), table)}
    if "source_mode" not in columns:
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ADD COLUMN {quote('source_mode')} varchar(8) NOT NULL DEFAULT 'CR'"
        )
    if "source_change_id" not in columns:
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ADD COLUMN {quote('source_change_id')} varchar(255) NULL"
        )

    # 不使用统一默认值。保留原 change_key；没有 change_key 的旧行使用主键兜底。
    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT r.id, r.change_key, COALESCE(repo.mode, 'CR') "
            f"FROM {quote(table)} r LEFT JOIN compliance_repository repo ON repo.id = r.repository_id ORDER BY r.id"
        )
        rows = cursor.fetchall()
        for record_id, change_key, source_mode in rows:
            source_change_id = str(change_key or '').strip() or f'legacy-{record_id}'
            cursor.execute(
                f"UPDATE {quote(table)} SET {quote('source_mode')}=%s, {quote('source_change_id')}=%s WHERE id=%s",
                [source_mode if source_mode in {'CR', 'MR'} else 'CR', source_change_id, record_id],
            )

    # 旧的唯一约束只覆盖 repository/branch/change_key，必须删除后才能建立来源维度约束。
    constraints = connection.introspection.get_constraints(connection.cursor(), table)
    if "cc_contribution_record_uniq" in constraints:
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} DROP INDEX {quote('cc_contribution_record_uniq')}"
        )
    constraints = connection.introspection.get_constraints(connection.cursor(), table)
    if "cc_contribution_record_source_uniq" not in constraints:
        schema_editor.execute(
            f"ALTER TABLE {quote(table)} ADD CONSTRAINT {quote('cc_contribution_record_source_uniq')} "
            f"UNIQUE ({quote('repository_id')}, {quote('branch_name')}, {quote('source_mode')}, {quote('source_change_id')})"
        )


class Migration(migrations.Migration):
    dependencies = [("code_compliance", "0012_contribution_mr_source")]

    operations = [migrations.RunPython(repair_contribution_source_identity, migrations.RunPython.noop)]
