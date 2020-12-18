# Generated by Django 3.1.4 on 2020-12-18 00:43

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("data", "0026_auto_20201218_0015"),
    ]

    operations = [
        migrations.AddField(
            model_name="goal",
            name="user",
            field=models.ForeignKey(default=10, on_delete=django.db.models.deletion.CASCADE, to="auth.user"),
            preserve_default=False,
        ),
    ]