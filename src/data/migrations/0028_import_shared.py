# Generated by Django 3.1.4 on 2020-12-18 01:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0027_goal_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="import",
            name="shared",
            field=models.BooleanField(default=False, help_text="Allow others to see and use this import?"),
        ),
    ]
