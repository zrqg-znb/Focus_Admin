import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('tools', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='agentskillprovider',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='tools_agent_skill_providers', to='core.user', verbose_name='所属用户'),
        ),
    ]
