# Generated by Django 3.1.4 on 2020-12-11 02:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0022_auto_20201211_0225"),
    ]

    operations = [
        migrations.RenameField(
            model_name="userlist",
            old_name="minimum_frequency",
            new_name="minimum_abs_frequency",
        ),
        migrations.AddField(
            model_name="userlist",
            name="minimum_doc_frequency",
            field=models.IntegerField(default=-1),
        ),
    ]
