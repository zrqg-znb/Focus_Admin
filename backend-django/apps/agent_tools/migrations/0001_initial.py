import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [('core', '0009_alter_permission_code')]

    operations = [
        migrations.CreateModel(
            name='AgentSkillProvider',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='档案名称')),
                ('owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tools_agent_skill_providers', to='core.user', verbose_name='所属用户')),
                ('base_url', models.URLField(max_length=500, verbose_name='API Base URL')),
                ('model', models.CharField(max_length=200, verbose_name='模型名称')),
                ('api_key_encrypted', models.TextField(blank=True, default='', verbose_name='加密 API Key')),
                ('is_active', models.BooleanField(db_index=True, default=True, verbose_name='是否启用')),
                ('description', models.TextField(blank=True, default='', verbose_name='说明')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ], options={'db_table': 'tools_skill_optimizer_provider', 'ordering': ['is_deleted', '-is_active', 'name']},
        ),
        migrations.CreateModel(
            name='AgentSkill',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('name', models.CharField(db_index=True, max_length=160, verbose_name='技能名称')),
                ('description', models.TextField(blank=True, default='', verbose_name='技能说明')),
                ('original_filename', models.CharField(max_length=255, verbose_name='原始文件名')),
                ('archive_content', models.BinaryField(verbose_name='原始 ZIP 内容')),
                ('file_manifest', models.JSONField(default=list, verbose_name='文件清单')),
                ('original_skill_md', models.TextField(verbose_name='原始 SKILL.md')),
                ('latest_skill_md', models.TextField(blank=True, default='', verbose_name='最新 SKILL.md')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ], options={'db_table': 'tools_skill_optimizer_skill', 'ordering': ['is_deleted', '-sys_create_datetime']},
        ),
        migrations.CreateModel(
            name='AgentSkillRun',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('provider_snapshot', models.JSONField(default=dict, verbose_name='模型配置快照')),
                ('status', models.CharField(choices=[('draft', '待配置'), ('queued', '排队中'), ('running', '运行中'), ('completed', '已完成'), ('failed', '失败'), ('cancelled', '已取消')], db_index=True, default='draft', max_length=20, verbose_name='状态')),
                ('max_rounds', models.PositiveSmallIntegerField(default=5, verbose_name='最大轮数')),
                ('scenarios', models.JSONField(default=list, verbose_name='测试场景')),
                ('evaluations', models.JSONField(default=list, verbose_name='评估标准')),
                ('baseline_score', models.FloatField(default=0, verbose_name='基线评分')),
                ('final_score', models.FloatField(default=0, verbose_name='最终评分')),
                ('original_skill_md', models.TextField(blank=True, default='', verbose_name='本次原始 SKILL.md')),
                ('improved_skill_md', models.TextField(blank=True, default='', verbose_name='优化后 SKILL.md')),
                ('error_message', models.TextField(blank=True, default='', verbose_name='失败信息')),
                ('cancel_requested', models.BooleanField(default=False, verbose_name='请求取消')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='开始时间')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='完成时间')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='runs', to='tools.agentskillprovider', verbose_name='模型档案')),
                ('skill', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='tools.agentskill', verbose_name='技能')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ], options={'db_table': 'tools_skill_optimizer_run', 'ordering': ['-sys_create_datetime']},
        ),
        migrations.CreateModel(
            name='AgentSkillIteration',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('round_number', models.PositiveSmallIntegerField(verbose_name='轮次')),
                ('status', models.CharField(db_index=True, max_length=20, verbose_name='状态')),
                ('score_before', models.FloatField(default=0, verbose_name='变更前评分')),
                ('score_after', models.FloatField(default=0, verbose_name='变更后评分')),
                ('kept', models.BooleanField(default=False, verbose_name='是否保留')),
                ('strategy', models.CharField(blank=True, default='', max_length=80, verbose_name='改写策略')),
                ('diagnosis', models.TextField(blank=True, default='', verbose_name='失败诊断')),
                ('description', models.TextField(blank=True, default='', verbose_name='变更说明')),
                ('evaluation_summary', models.JSONField(default=list, verbose_name='评估汇总')),
                ('run', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='iterations', to='tools.agentskillrun', verbose_name='优化任务')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ], options={'db_table': 'tools_skill_optimizer_iteration', 'ordering': ['round_number'], 'unique_together': {('run', 'round_number')}},
        ),
        migrations.AddIndex(model_name='agentskillrun', index=models.Index(fields=['status', '-sys_create_datetime'], name='tools_agent_status_ef33ef_idx')),
        migrations.AddIndex(model_name='agentskillrun', index=models.Index(fields=['skill', '-sys_create_datetime'], name='tools_agent_skill_i_b6438a_idx')),
    ]
