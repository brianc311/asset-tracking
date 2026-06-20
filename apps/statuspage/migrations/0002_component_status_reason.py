from django.db import migrations, models


def migrate_legacy_statuses(apps, schema_editor):
    SystemComponent = apps.get_model("statuspage", "SystemComponent")
    mapping = {
        "partial": "degraded",
        "major": "offline",
        "maintenance": "degraded",
    }
    for component in SystemComponent.objects.all():
        new_status = mapping.get(component.status)
        if new_status:
            component.status = new_status
            component.save(update_fields=["status"])


class Migration(migrations.Migration):

    dependencies = [
        ("statuspage", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="systemcomponent",
            name="status_reason",
            field=models.TextField(
                blank=True,
                help_text="Shown on the public status page when degraded or offline.",
            ),
        ),
        migrations.AlterField(
            model_name="systemcomponent",
            name="status",
            field=models.CharField(
                choices=[
                    ("operational", "Operational"),
                    ("degraded", "Degraded"),
                    ("offline", "Offline"),
                ],
                default="operational",
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_legacy_statuses, migrations.RunPython.noop),
    ]
