from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0021_booking_client_timezone"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="booking",
            name="client_timezone",
        ),
    ]
