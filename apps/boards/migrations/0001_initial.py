# Generated by Django 5.1.4 on 2025-01-03 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Board',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100)),
                ('key', models.CharField(max_length=10)),
            ],
            options={
                'verbose_name': 'Board',
                'verbose_name_plural': 'Boards',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='BoardSection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=50)),
                ('max_issues_limit', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name': 'Board Section',
                'verbose_name_plural': 'Board Sections',
                'ordering': ['created_at'],
            },
        ),
    ]