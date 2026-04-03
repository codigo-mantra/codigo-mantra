from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0020_remove_unique_consultant_booking"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="client_timezone",
            field=models.CharField(
                blank=True,
                default="Asia/Kolkata",
                max_length=100,
            ),
        ),
    ]
