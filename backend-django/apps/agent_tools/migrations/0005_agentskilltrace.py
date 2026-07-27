import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """保存 Skill Optimizer 每次模型调用的实时审计轨迹。"""

    dependencies = [('tools', '0004_rename_skill_optimizer_indexes')]

    operations = [
        migrations.CreateModel(
            name='AgentSkillTrace',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('round_number', models.PositiveSmallIntegerField(default=0, verbose_name='轮次')),
                ('stage', models.CharField(db_index=True, max_length=50, verbose_name='调用阶段')),
                ('status', models.CharField(db_index=True, default='running', max_length=20, verbose_name='调用状态')),
                ('request_content', models.TextField(blank=True, default='', verbose_name='请求内容')),
                ('response_content', models.TextField(blank=True, default='', verbose_name='响应内容')),
                ('error_message', models.TextField(blank=True, default='', verbose_name='失败信息')),
                ('duration_ms', models.PositiveIntegerField(default=0, verbose_name='耗时毫秒')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='traces', to='tools.agentskillrun', verbose_name='优化任务')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ],
            options={'db_table': 'tools_skill_optimizer_trace', 'ordering': ['sys_create_datetime']},
        ),
        migrations.AddIndex(
            model_name='agentskilltrace',
            index=models.Index(fields=['run', 'sys_create_datetime'], name='tools_skill_run_id_42e600_idx'),
        ),
    ]
