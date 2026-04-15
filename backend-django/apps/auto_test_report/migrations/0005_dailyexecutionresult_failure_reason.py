from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0004_testcase_remark'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyexecutionresult',
            name='failure_reason',
            field=models.TextField(blank=True, null=True, verbose_name='异常原因'),
        ),
    ]
