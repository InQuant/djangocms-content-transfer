# Generated by Django 5.2 on 2025-04-14 08:55

import cmstransfer.serializers
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cmstransfer', '0001_initial'),
        ('djangocms_alias', '0004_alter_aliascontent_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='AliasImport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(blank=True, default=dict, encoder=cmstransfer.serializers.JsonEncoder)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(blank=True, default='', max_length=100)),
            ],
            options={
                'verbose_name': 'Alias Import',
            },
        ),
        migrations.AlterField(
            model_name='pageexport',
            name='data',
            field=models.JSONField(blank=True, default=dict, encoder=cmstransfer.serializers.JsonEncoder),
        ),
        migrations.AlterField(
            model_name='pageexport',
            name='recursive',
            field=models.BooleanField(default=False, help_text='Exports selected page recursive with all child pages.'),
        ),
        migrations.AlterField(
            model_name='pageimport',
            name='data',
            field=models.JSONField(blank=True, default=dict, encoder=cmstransfer.serializers.JsonEncoder),
        ),
        migrations.CreateModel(
            name='AliasExport',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField(blank=True, default=dict, encoder=cmstransfer.serializers.JsonEncoder)),
                ('modified_at', models.DateTimeField(auto_now=True)),
                ('alias', models.ForeignKey(help_text='Select Alias to export.', on_delete=django.db.models.deletion.CASCADE, related_name='+', to='djangocms_alias.alias')),
            ],
            options={
                'verbose_name': 'Alias Export',
            },
        ),
    ]
