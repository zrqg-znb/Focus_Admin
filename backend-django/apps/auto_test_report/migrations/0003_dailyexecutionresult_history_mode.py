from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0002_remove_vehiclemodel_report_token'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='dailyexecutionresult',
            name='uniq_atr_vehicle_date_case',
        ),
        migrations.AddIndex(
            model_name='dailyexecutionresult',
            index=models.Index(
                fields=['vehicle', 'execute_date', 'test_case'],
                name='idx_atr_res_vehicle_date_case',
            ),
        ),
        migrations.AddIndex(
            model_name='dailyexecutionresult',
            index=models.Index(
                fields=['test_case', 'vehicle', 'execute_date'],
                name='idx_atr_res_case_vehicle_date',
            ),
        ),
        migrations.AddIndex(
            model_name='dailyexecutionresult',
            index=models.Index(
                fields=[
                    'vehicle',
                    'execute_date',
                    'test_case',
                    'start_time',
                    'reported_at',
                    'sys_create_datetime',
                ],
                name='idx_atr_res_latest_lookup',
            ),
        ),
    ]
