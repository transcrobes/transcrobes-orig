# Generated by Django 3.1.6 on 2021-02-14 01:54

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0033_auto_20210213_1337"),
    ]

    operations = [
        migrations.AlterField(
            model_name="content",
            name="the_import",
            field=models.OneToOneField(
                help_text="Source import", on_delete=django.db.models.deletion.CASCADE, to="data.import"
            ),
        ),
    ]
