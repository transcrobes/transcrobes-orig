# Generated by Django 3.1.7 on 2021-03-04 05:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0044_card"),
    ]

    operations = [
        migrations.AlterField(
            model_name="card",
            name="efactor",
            field=models.FloatField(default=2.5, help_text="SM2 efactor"),
        ),
    ]
