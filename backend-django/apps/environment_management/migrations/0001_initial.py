# Generated manually for environment_management initial schema.

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0009_alter_permission_code'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestEnvironment',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('ip_address', models.GenericIPAddressField(help_text='远程环境 IP 地址', verbose_name='IP地址')),
                ('account', models.CharField(blank=True, default='', max_length=100, verbose_name='账号')),
                ('password_encrypted', models.TextField(blank=True, default='', verbose_name='加密密码')),
                ('domain', models.CharField(choices=[('cockpit', '座舱'), ('vehicle', '车控')], db_index=True, default='cockpit', max_length=20, verbose_name='领域')),
                ('category', models.CharField(choices=[('dev', '开发'), ('test', '测试'), ('ci', 'CI')], db_index=True, default='test', max_length=20, verbose_name='环境分类')),
                ('project_name', models.CharField(blank=True, db_index=True, default='', max_length=100, verbose_name='项目名称')),
                ('vehicle_model', models.CharField(blank=True, db_index=True, default='', max_length=100, verbose_name='车型')),
                ('device_material', models.CharField(blank=True, default='', max_length=100, verbose_name='测试设备物料')),
                ('asset_number', models.CharField(blank=True, default='', max_length=100, verbose_name='资产编号')),
                ('config', models.JSONField(blank=True, default=dict, verbose_name='配置情况')),
                ('shelf_location', models.CharField(blank=True, default='', max_length=200, verbose_name='货架位置')),
                ('status', models.CharField(choices=[('idle', '空闲'), ('occupied', '占用中')], db_index=True, default='idle', max_length=20, verbose_name='状态')),
                ('occupied_at', models.DateTimeField(blank=True, null=True, verbose_name='占用开始时间')),
                ('current_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='occupied_test_environments', to='core.user', verbose_name='当前占用人')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ],
            options={
                'verbose_name': '测试环境',
                'verbose_name_plural': '测试环境',
                'db_table': 'environment_management_environment',
                'ordering': ['is_deleted', '-sort', 'ip_address'],
            },
        ),
        migrations.CreateModel(
            name='EnvironmentFavorite',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('environment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to='environment_management.testenvironment', verbose_name='环境')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='environment_favorites', to='core.user', verbose_name='用户')),
            ],
            options={
                'verbose_name': '环境收藏',
                'verbose_name_plural': '环境收藏',
                'db_table': 'environment_management_favorite',
                'unique_together': {('environment', 'user')},
            },
        ),
        migrations.CreateModel(
            name='EnvironmentQueue',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('queue_type', models.CharField(choices=[('normal', '排队'), ('jump', '插队')], default='normal', max_length=20, verbose_name='队列类型')),
                ('status', models.CharField(choices=[('waiting', '等待中'), ('cancelled', '已取消'), ('done', '已完成')], db_index=True, default='waiting', max_length=20, verbose_name='状态')),
                ('position', models.IntegerField(db_index=True, default=0, verbose_name='排序位置')),
                ('requested_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='申请时间')),
                ('environment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='queues', to='environment_management.testenvironment', verbose_name='环境')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='environment_queues', to='core.user', verbose_name='用户')),
            ],
            options={
                'verbose_name': '环境队列',
                'verbose_name_plural': '环境队列',
                'db_table': 'environment_management_queue',
                'ordering': ['position', 'requested_at'],
            },
        ),
        migrations.CreateModel(
            name='EnvironmentRecord',
            fields=[
                ('id', models.CharField(default=uuid.uuid4, editable=False, help_text='主键ID', max_length=36, primary_key=True, serialize=False)),
                ('sys_create_datetime', models.DateTimeField(auto_now_add=True, db_index=True, help_text='创建时间')),
                ('sys_update_datetime', models.DateTimeField(auto_now=True, db_index=True, help_text='更新时间')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='是否删除（软删除标识）')),
                ('sort', models.IntegerField(db_index=True, default=0, help_text='排序（数字越大越靠前）')),
                ('action', models.CharField(choices=[('occupy', '占用'), ('release', '释放'), ('queue', '排队'), ('cancel_queue', '取消排队'), ('jump_queue', '插队'), ('admin_update', '管理员更新')], db_index=True, max_length=30, verbose_name='动作')),
                ('message', models.CharField(blank=True, default='', max_length=500, verbose_name='说明')),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='占用开始时间')),
                ('ended_at', models.DateTimeField(blank=True, null=True, verbose_name='占用结束时间')),
                ('duration_seconds', models.IntegerField(default=0, verbose_name='持续时长')),
                ('snapshot', models.JSONField(blank=True, default=dict, verbose_name='快照')),
                ('environment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='records', to='environment_management.testenvironment', verbose_name='环境')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='environment_records', to='core.user', verbose_name='操作人')),
                ('sys_creator', models.ForeignKey(blank=True, db_constraint=False, help_text='创建人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_created', to='core.user')),
                ('sys_modifier', models.ForeignKey(blank=True, db_constraint=False, help_text='修改人', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(app_label)s_%(class)s_modified', to='core.user')),
            ],
            options={
                'verbose_name': '环境操作记录',
                'verbose_name_plural': '环境操作记录',
                'db_table': 'environment_management_record',
                'ordering': ['-sys_create_datetime'],
            },
        ),
        migrations.AddIndex(model_name='testenvironment', index=models.Index(fields=['domain', 'category'], name='environment_domain_927599_idx')),
        migrations.AddIndex(model_name='testenvironment', index=models.Index(fields=['status', 'current_user'], name='environment_status_52abfe_idx')),
        migrations.AddIndex(model_name='testenvironment', index=models.Index(fields=['project_name', 'vehicle_model'], name='environment_project_577fba_idx')),
        migrations.AddIndex(model_name='environmentfavorite', index=models.Index(fields=['user', 'environment'], name='environment_user_id_60e74a_idx')),
        migrations.AddIndex(model_name='environmentqueue', index=models.Index(fields=['environment', 'status', 'position'], name='environment_environ_8bd7ae_idx')),
        migrations.AddIndex(model_name='environmentqueue', index=models.Index(fields=['environment', 'user', 'status'], name='environment_environ_ca48cd_idx')),
        migrations.AddIndex(model_name='environmentrecord', index=models.Index(fields=['environment', '-sys_create_datetime'], name='environment_environ_37b321_idx')),
        migrations.AddIndex(model_name='environmentrecord', index=models.Index(fields=['operator', '-sys_create_datetime'], name='environment_operato_3ff8c3_idx')),
    ]
