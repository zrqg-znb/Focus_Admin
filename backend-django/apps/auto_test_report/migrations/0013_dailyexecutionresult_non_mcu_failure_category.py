from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0012_vehiclemodel_responsible_users'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dailyexecutionresult',
            name='failure_category',
            field=models.CharField(
                blank=True,
                choices=[
                    ('version', '版本问题'),
                    ('environment', '环境问题'),
                    ('case', '用例问题'),
                    ('non_mcu', '非MCU问题'),
                ],
                db_index=True,
                max_length=32,
                null=True,
                verbose_name='失败根因大类',
            ),
        ),
    ]
