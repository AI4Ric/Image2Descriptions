# Generated by Django 4.2.7 on 2023-12-01 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AIDescGen', '0002_userupload_folder_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userupload',
            name='folder_name',
            field=models.CharField(default='default_folder_name', editable=False, max_length=255),
        ),
    ]
