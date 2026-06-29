from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('environment_management', '0004_environment_device_binding_and_assets'),
    ]

    operations = [
        migrations.AlterField(
            model_name='environmentrecord',
            name='action',
            field=models.CharField(
                choices=[
                    ('occupy', '占用'),
                    ('release', '释放'),
                    ('queue', '排队'),
                    ('cancel_queue', '取消排队'),
                    ('jump_queue', '插队'),
                    ('auto_release', '自动释放'),
                    ('admin_update', '管理员更新'),
                ],
                db_index=True,
                max_length=30,
                verbose_name='动作',
            ),
        ),
    ]
