from django.db import migrations, models


def _migrate_repository_types(apps, schema_editor):
    AuditProject = apps.get_model('deepaudit', 'AuditProject')
    AuditProject.objects.exclude(repository_type__in=['single', 'multi']).update(repository_type='single')


class Migration(migrations.Migration):

    dependencies = [
        ('deepaudit', '0004_alter_agentcheckpoint_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='auditproject',
            name='manifest_xml',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='Manifest XML'),
        ),
        migrations.AddField(
            model_name='auditproject',
            name='group',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Group'),
        ),
        migrations.AlterField(
            model_name='auditproject',
            name='repository_type',
            field=models.CharField(choices=[('single', '单仓'), ('multi', '多仓')], default='single', max_length=20, verbose_name='仓库类型'),
        ),
        migrations.AddField(
            model_name='audittask',
            name='manifest_xml',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='Manifest XML'),
        ),
        migrations.AddField(
            model_name='audittask',
            name='group',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Group'),
        ),
        migrations.AddField(
            model_name='agenttask',
            name='manifest_xml',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='Manifest XML'),
        ),
        migrations.AddField(
            model_name='agenttask',
            name='group',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Group'),
        ),
        migrations.RunPython(_migrate_repository_types, migrations.RunPython.noop),
    ]
