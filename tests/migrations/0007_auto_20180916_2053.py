# Generated by Django 2.1 on 2018-09-17 00:53

from django.db import migrations
import django.db.models.deletion
import opinionated_reporting.fields


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0006_orderedfact_total'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderedfact',
            name='created_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordered_created_on', to='opinionated_reporting.DateDimension'),
        ),
        migrations.AlterField(
            model_name='orderedfact',
            name='customer',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='tests.CustomerDimension'),
        ),
        migrations.AlterField(
            model_name='orderedfact',
            name='hour_created_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordered_hour_created_on', to='opinionated_reporting.HourDimension'),
        ),
        migrations.AlterField(
            model_name='orderedfact',
            name='hour_ordered_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordered_hour_ordered_on', to='opinionated_reporting.HourDimension'),
        ),
        migrations.AlterField(
            model_name='orderedfact',
            name='ordered_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='ordered_ordered_on', to='opinionated_reporting.DateDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='created_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orderedproduct_created_on', to='opinionated_reporting.DateDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='customer',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='tests.CustomerDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='hour_created_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orderedproduct_hour_created_on', to='opinionated_reporting.HourDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='hour_ordered_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orderedproduct_hour_ordered_on', to='opinionated_reporting.HourDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='ordered_on',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='orderedproduct_ordered_on', to='opinionated_reporting.DateDimension'),
        ),
        migrations.AlterField(
            model_name='orderedproductfact',
            name='product',
            field=opinionated_reporting.fields.DimensionForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='tests.ProductDimension'),
        ),
    ]
