from django.db import migrations, models
import django.db.models.deletion
import uuid


def _copy_legacy_approvers(apps, schema_editor):
    """把旧版审批人员平滑迁移为责任田看护人候选。"""
    responsibility_model = apps.get_model('code_quality_governance', 'GovernanceResponsibility')
    for responsibility in responsibility_model.objects.all():
        responsibility.caretakers.add(*responsibility.approvers.all())


class Migration(migrations.Migration):
    """为治理工作台增加看护人、关系聚合和审计数据。"""

    dependencies = [('code_quality_governance', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='governanceresponsibility',
            name='caretakers',
            field=models.ManyToManyField(
                blank=True,
                related_name='governance_responsibility_caretakers',
                to='core.user',
                verbose_name='看护人',
            ),
        ),
        migrations.RunPython(
            code=_copy_legacy_approvers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AddField(model_name='governanceprojectresponsibility', name='finding_count', field=models.PositiveIntegerField(default=0, verbose_name='问题数量')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='normal_count', field=models.PositiveIntegerField(default=0, verbose_name='待治理数量')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='pending_count', field=models.PositiveIntegerField(default=0, verbose_name='问题屏蔽申请中数量')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='shielded_count', field=models.PositiveIntegerField(default=0, verbose_name='已屏蔽数量')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='pending_application_count', field=models.PositiveIntegerField(default=0, verbose_name='待审批申请数量')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='last_scan_at', field=models.DateTimeField(blank=True, null=True, verbose_name='最近扫描时间')),
        migrations.AddField(model_name='governanceprojectresponsibility', name='last_scan_status', field=models.CharField(blank=True, default='', max_length=20, verbose_name='最近扫描状态')),
        migrations.CreateModel(
            name='GovernanceCaretakerAuditLog',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('action', models.CharField(choices=[('add', '添加看护人'), ('remove', '移除看护人')], max_length=20, verbose_name='操作类型')),
                ('comment', models.TextField(blank=True, default='', verbose_name='操作说明')),
                ('caretaker', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='governance_caretaker_audit_logs', to='core.user', verbose_name='看护人')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='governance_caretaker_operators', to='core.user', verbose_name='操作人')),
                ('responsibility', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='caretaker_audit_logs', to='code_quality_governance.governanceresponsibility', verbose_name='责任田')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ],
            options={'db_table': 'agent_tools_governance_caretaker_audit_log', 'ordering': ['-sys_create_datetime']},
        ),
    ]
