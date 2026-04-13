from collections import defaultdict

from django.db import migrations


def recalculate_product_failure_mode_landing_cache(apps, schema_editor):
    ProductFailureMode = apps.get_model('project_manager', 'ProductFailureMode')
    ProductFailureModeInterceptionLanding = apps.get_model(
        'project_manager',
        'ProductFailureModeInterceptionLanding',
    )
    ProductFailureModeHandlingLanding = apps.get_model(
        'project_manager',
        'ProductFailureModeHandlingLanding',
    )
    ProductFailureModeObservationLanding = apps.get_model(
        'project_manager',
        'ProductFailureModeObservationLanding',
    )
    ProductFailureModeHuatuoLanding = apps.get_model(
        'project_manager',
        'ProductFailureModeHuatuoLanding',
    )

    flags_by_binding = defaultdict(list)
    landing_models = (
        ProductFailureModeInterceptionLanding,
        ProductFailureModeHandlingLanding,
        ProductFailureModeObservationLanding,
        ProductFailureModeHuatuoLanding,
    )

    for landing_model in landing_models:
        for product_failure_mode_id, is_landed in landing_model.objects.filter(
            is_deleted=False,
            product_failure_mode__is_deleted=False,
        ).values_list('product_failure_mode_id', 'is_landed'):
            flags_by_binding[product_failure_mode_id].append(bool(is_landed))

    for binding in ProductFailureMode.objects.filter(is_deleted=False).only('id'):
        flags = flags_by_binding.get(binding.id, [])
        ProductFailureMode.objects.filter(id=binding.id).update(
            is_landed=bool(flags) and all(flags),
        )


def noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ('project_manager', '0038_productfailuremode_landing_models_and_more'),
    ]

    operations = [
        migrations.RunPython(
            recalculate_product_failure_mode_landing_cache,
            noop,
        ),
    ]
