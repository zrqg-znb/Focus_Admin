from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("performance", "0002_alter_performanceindicator_owner"),
    ]

    operations = [
        migrations.AddField(
            model_name="performanceindicator",
            name="category",
            field=models.CharField(
                choices=[("vehicle", "车控"), ("cockpit", "座舱")],
                default="vehicle",
                help_text="分类",
                max_length=20,
                verbose_name="分类",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="performanceindicator",
            unique_together={("category", "project", "module", "chip_type", "name")},
        ),
    ]

