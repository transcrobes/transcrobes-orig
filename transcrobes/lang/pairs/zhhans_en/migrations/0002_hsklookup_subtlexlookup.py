# Generated by Django 2.1.5 on 2019-02-15 01:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zhhans_en', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HSKLookup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source_text', models.CharField(db_index=True, max_length=2000)),
                ('response_json', models.CharField(max_length=25000)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SubtlexLookup',
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
