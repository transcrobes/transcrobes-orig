# Generated by Django 3.1.6 on 2021-02-13 13:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0032_content"),
    ]

    operations = [
        migrations.AlterField(
            model_name="content",
            name="author",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name="content",
            name="cover",
            field=models.CharField(blank=True, max_length=250, null=True),
        ),
        migrations.AlterField(
            model_name="content",
            name="language",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
