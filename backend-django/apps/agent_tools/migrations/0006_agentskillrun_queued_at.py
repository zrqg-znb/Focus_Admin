from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('tools', '0005_agentskilltrace')]

    operations = [
        migrations.AddField(
            model_name='agentskillrun',
            name='queued_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='进入队列时间'),
        ),
    ]
