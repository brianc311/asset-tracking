from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0002_add_asset_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="asset",
            name="site_name",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Site or location group this asset belongs to.",
                max_length=120,
            ),
        ),
    ]
