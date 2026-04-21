from django.db import migrations, models


VALID_REPOSITORY_TYPES = {'single', 'multi'}


def _normalize_repository_type(value: str | None) -> str:
    return value if value in VALID_REPOSITORY_TYPES else 'single'


def _backfill_task_repository_snapshots(apps, schema_editor):
    AuditTask = apps.get_model('deepaudit', 'AuditTask')
    AgentTask = apps.get_model('deepaudit', 'AgentTask')

    for task in AuditTask.objects.select_related('project').all().iterator():
        project = getattr(task, 'project', None)
        AuditTask.objects.filter(pk=task.pk).update(
            repository_url=getattr(project, 'repository_url', None),
            repository_type=_normalize_repository_type(getattr(project, 'repository_type', None)),
        )

    for task in AgentTask.objects.select_related('project').all().iterator():
        project = getattr(task, 'project', None)
        AgentTask.objects.filter(pk=task.pk).update(
            repository_url=getattr(project, 'repository_url', None),
            repository_type=_normalize_repository_type(getattr(project, 'repository_type', None)),
        )


class Migration(migrations.Migration):

    dependencies = [
        ('deepaudit', '0005_codehub_multirepo_support'),
    ]

    operations = [
        migrations.AddField(
            model_name='audittask',
            name='repository_type',
            field=models.CharField(choices=[('single', '单仓'), ('multi', '多仓')], default='single', max_length=20, verbose_name='仓库类型快照'),
        ),
        migrations.AddField(
            model_name='audittask',
            name='repository_url',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='仓库地址快照'),
        ),
        migrations.AddField(
            model_name='agenttask',
            name='repository_type',
            field=models.CharField(choices=[('single', '单仓'), ('multi', '多仓')], default='single', max_length=20, verbose_name='仓库类型快照'),
        ),
        migrations.AddField(
            model_name='agenttask',
            name='repository_url',
            field=models.CharField(blank=True, max_length=1000, null=True, verbose_name='仓库地址快照'),
        ),
        migrations.RunPython(_backfill_task_repository_snapshots, migrations.RunPython.noop),
    ]
