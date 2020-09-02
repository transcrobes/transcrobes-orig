# Generated by Django 2.1.1 on 2018-09-10 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("enrich", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BingAPITranslation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_text", models.CharField(max_length=200)),
                ("response_json", models.CharField(max_length=25000)),
            ],
            options={"abstract": False},
        ),
        migrations.RenameModel(
            old_name="BingRequest",
            new_name="BingAPILookup",
        ),
    ]