from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0013_dailyexecutionresult_non_mcu_failure_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mcuplatform',
            name='domain',
            field=models.CharField(
                choices=[
                    ('cockpit', '座舱MCU'),
                    ('cockpit_soc', '座舱SOC'),
                    ('vehicle', '车控'),
                    ('vehicle_io', '车控IO'),
                ],
                db_index=True,
                default='cockpit',
                max_length=16,
                verbose_name='领域',
            ),
        ),
    ]
