# Generated by Django 3.1.3 on 2020-11-29 05:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0016_import_process_type"),
    ]

    operations = [
        migrations.AlterField(
            model_name="import",
            name="processed",
            field=models.BooleanField(default=False, null=True),
        ),
    ]
