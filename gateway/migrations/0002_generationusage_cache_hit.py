from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("gateway", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="generationusage",
            name="cache_hit",
            field=models.BooleanField(default=False),
        ),
    ]
