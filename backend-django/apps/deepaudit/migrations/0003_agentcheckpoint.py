import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('deepaudit', '0002_alter_auditissue_message'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentCheckpoint',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('agent_id', models.CharField(db_index=True, max_length=50, verbose_name='Agent ID')),
                ('agent_name', models.CharField(max_length=255, verbose_name='Agent 名称')),
                ('agent_type', models.CharField(max_length=50, verbose_name='Agent 类型')),
                ('parent_agent_id', models.CharField(blank=True, max_length=50, null=True, verbose_name='父 Agent ID')),
                ('state_data', models.JSONField(blank=True, default=dict, verbose_name='状态快照')),
                ('iteration', models.IntegerField(default=0, verbose_name='迭代次数')),
                ('status', models.CharField(db_index=True, max_length=30, verbose_name='状态')),
                ('total_tokens', models.IntegerField(default=0, verbose_name='累计 Token')),
                ('tool_calls', models.IntegerField(default=0, verbose_name='工具调用次数')),
                ('findings_count', models.IntegerField(default=0, verbose_name='发现数量')),
                ('checkpoint_type', models.CharField(default='auto', max_length=30, verbose_name='检查点类型')),
                ('checkpoint_name', models.CharField(blank=True, max_length=255, null=True, verbose_name='检查点名称')),
                ('checkpoint_metadata', models.JSONField(blank=True, default=dict, verbose_name='检查点元数据')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deepaudit_agentcheckpoint_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='deepaudit_agentcheckpoint_modified', to='core.user')),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='persisted_checkpoints', to='deepaudit.agenttask', verbose_name='所属任务')),
            ],
            options={
                'verbose_name': 'DeepAudit Agent 检查点',
                'verbose_name_plural': 'DeepAudit Agent 检查点',
                'db_table': 'deepaudit_agent_checkpoint',
                'ordering': ['is_deleted', '-sort', '-sys_create_datetime'],
                'indexes': [
                    models.Index(fields=['task', 'agent_id'], name='deepaudit_a_task_id_96a1b2_idx'),
                    models.Index(fields=['task', 'sys_create_datetime'], name='deepaudit_a_task_id_35ef0e_idx'),
                    models.Index(fields=['task', 'checkpoint_type'], name='deepaudit_a_task_id_4ee2b5_idx'),
                ],
            },
        ),
    ]
