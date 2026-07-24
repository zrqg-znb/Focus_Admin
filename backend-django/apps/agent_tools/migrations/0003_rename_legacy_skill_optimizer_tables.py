from django.db import migrations


LEGACY_TABLES = {
    'tools_agent_skills_provider': 'tools_skill_optimizer_provider',
    'tools_agent_skills_skill': 'tools_skill_optimizer_skill',
    'tools_agent_skills_run': 'tools_skill_optimizer_run',
    'tools_agent_skills_iteration': 'tools_skill_optimizer_iteration',
}


def rename_legacy_tables(apps, schema_editor):
    """升级已有部署时保留 Skill Optimizer 的历史数据。"""
    existing_tables = set(schema_editor.connection.introspection.table_names())
    for legacy_name, current_name in LEGACY_TABLES.items():
        if legacy_name in existing_tables and current_name not in existing_tables:
            schema_editor.execute(
                f'ALTER TABLE {schema_editor.quote_name(legacy_name)} RENAME TO {schema_editor.quote_name(current_name)}'
            )


class Migration(migrations.Migration):
    # SQLite 不支持在可回滚事务中执行 ALTER TABLE；本迁移仅处理存在的历史表。
    atomic = False
    dependencies = [('tools', '0002_agentskillprovider_owner')]

    operations = [migrations.RunPython(rename_legacy_tables, migrations.RunPython.noop)]
