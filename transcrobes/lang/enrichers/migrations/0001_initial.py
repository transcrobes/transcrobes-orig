# Generated by Django 2.1.5 on 2019-02-18 07:24

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CMULookup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_text', models.CharField(db_index=True, max_length=2000)),
                ('response_json', models.CharField(max_length=25000)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]