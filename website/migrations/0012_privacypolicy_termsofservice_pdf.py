from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0011_privacypolicy_termsofservice_alter_contactus_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='privacypolicy',
            name='pdf',
            field=models.FileField(blank=True, null=True, upload_to='documents/privacy_policy/'),
        ),
        migrations.AddField(
            model_name='termsofservice',
            name='pdf',
            field=models.FileField(blank=True, null=True, upload_to='documents/terms_of_service/'),
        ),
    ]
