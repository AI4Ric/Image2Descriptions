# Generated by Django 4.2.7 on 2023-12-05 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AIDescGen', '0003_alter_userupload_folder_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='userupload',
            name='task_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]