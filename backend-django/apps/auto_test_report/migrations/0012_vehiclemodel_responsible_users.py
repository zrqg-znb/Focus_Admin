from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0011_cockpit_soc_domain_and_test_case_module'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclemodel',
            name='responsible_users',
            field=models.ManyToManyField(
                blank=True,
                related_name='auto_test_report_responsible_vehicles',
                to='core.user',
                verbose_name='责任人',
            ),
        ),
    ]
