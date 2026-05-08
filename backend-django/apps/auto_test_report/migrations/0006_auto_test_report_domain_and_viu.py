from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0005_dailyexecutionresult_failure_reason'),
    ]

    operations = [
        migrations.AddField(
            model_name='mcuplatform',
            name='domain',
            field=models.CharField(
                choices=[('cockpit', '座舱'), ('vehicle', '车控')],
                db_index=True,
                default='cockpit',
                max_length=16,
                verbose_name='领域',
            ),
        ),
        migrations.AddField(
            model_name='vehiclemodel',
            name='viu_codes',
            field=models.JSONField(blank=True, default=list, verbose_name='可用VIU编号'),
        ),
        migrations.AddField(
            model_name='testcase',
            name='viu_code',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='VIU编号'),
        ),
        migrations.RemoveConstraint(
            model_name='testcase',
            name='uniq_atr_vehicle_case_no',
        ),
        migrations.AddConstraint(
            model_name='testcase',
            constraint=models.UniqueConstraint(
                fields=('vehicle', 'viu_code', 'case_no'),
                name='uniq_atr_vehicle_viu_case_no',
            ),
        ),
    ]
