from django.db import migrations


class Migration(migrations.Migration):
    """使运行记录索引名称与 Skill Optimizer 数据表保持一致。"""

    dependencies = [('tools', '0003_rename_legacy_skill_optimizer_tables')]

    operations = [
        migrations.RenameIndex(
            model_name='agentskillrun',
            new_name='tools_skill_status_e65599_idx',
            old_name='tools_agent_status_ef33ef_idx',
        ),
        migrations.RenameIndex(
            model_name='agentskillrun',
            new_name='tools_skill_skill_i_f8d68e_idx',
            old_name='tools_agent_skill_i_b6438a_idx',
        ),
    ]
