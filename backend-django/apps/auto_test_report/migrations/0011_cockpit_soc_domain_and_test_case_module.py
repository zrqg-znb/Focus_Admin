from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0010_remove_downstreamcommit_unused_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mcuplatform',
            name='domain',
            field=models.CharField(
                choices=[('cockpit', '座舱MCU'), ('cockpit_soc', '座舱SOC'), ('vehicle', '车控')],
                db_index=True,
                default='cockpit',
                max_length=16,
                verbose_name='领域',
            ),
        ),
        migrations.AddField(
            model_name='testcase',
            name='module',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='模块'),
        ),
    ]
