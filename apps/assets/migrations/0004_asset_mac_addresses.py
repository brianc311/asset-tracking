from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_asset_site_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="mac_address",
            field=models.CharField(blank=True, db_index=True, max_length=17),
        ),
        migrations.AddField(
            model_name="asset",
            name="mac_address_2",
            field=models.CharField(blank=True, db_index=True, max_length=17),
        ),
    ]
