from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0019_rename_google_meet_link_booking_meet_link"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="booking",
            name="unique_consultant_booking",
        ),
    ]

