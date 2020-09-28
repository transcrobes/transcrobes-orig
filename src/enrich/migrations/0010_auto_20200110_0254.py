# Generated by Django 2.2.8 on 2020-01-10 02:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("enrich", "0009_auto_20200110_0253"),
    ]

    operations = [
        migrations.RemoveConstraint(model_name="bingapilookup", name="unique_trans",),
        migrations.AddConstraint(
            model_name="bingapilookup",
            constraint=models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_lkp"),
        ),
        migrations.AddConstraint(
            model_name="bingapitranslation",
            constraint=models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tla"),
        ),
        migrations.AddConstraint(
            model_name="bingapitransliteration",
            constraint=models.UniqueConstraint(fields=("source_text", "from_lang", "to_lang"), name="unique_trans_tli"),
        ),
    ]
