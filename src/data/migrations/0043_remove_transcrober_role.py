# Generated by Django 3.1.7 on 2021-03-02 06:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0042_auto_20210302_0629"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="transcrober",
            name="role",
        ),
    ]