# Generated by Django 2.1 on 2018-09-17 00:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0005_auto_20180916_1530'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderedfact',
            name='total',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
