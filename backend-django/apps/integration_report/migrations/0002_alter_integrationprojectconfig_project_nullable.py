import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integration_report', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='integrationprojectconfig',
            name='project',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='integration_configs',
                to='project_manager.project',
                verbose_name='所属项目',
            ),
        ),
    ]

