from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auto_test_report', '0009_downstreamcommit_downstreamcommitusage_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='downstreamcommit',
            name='build_url',
        ),
        migrations.RemoveField(
            model_name='downstreamcommit',
            name='remark',
        ),
        migrations.RemoveField(
            model_name='downstreamcommit',
            name='source',
        ),
    ]
