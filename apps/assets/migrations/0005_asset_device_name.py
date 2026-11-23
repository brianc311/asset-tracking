from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0004_asset_mac_addresses"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="device_name",
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
