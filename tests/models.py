from django.db import models
from opinionated_reporting.models import BaseDimension, BaseFact, DateDimension, HourDimension
from opinionated_reporting.fields import DimensionForeignKey, IntegerDescriptionField


class TestProduct(models.Model):
    name = models.CharField(max_length=256)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        app_label = 'tests'


class TestCustomer(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=256)

    class Meta:
        app_label = 'tests'


class TestOrder(models.Model):
    customer = models.ForeignKey(TestCustomer, on_delete=models.CASCADE)
    products = models.ManyToManyField(TestProduct, through='TestOrderItem')
    created_on = models.DateTimeField(auto_now_add=True)
    ordered_on = models.DateTimeField(null=True, blank=True, default=None)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    tax = models.DecimalField(max_digits=10, decimal_places=2)
    cancelled = models.BooleanField(default=False)

    class Meta:
        app_label = 'tests'


class TestOrderItem(models.Model):
    order = models.ForeignKey(TestOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(TestProduct, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        app_label = 'tests'


class CustomerDimension(BaseDimension):

    class ReportingMeta:
        business_model = TestCustomer
        unique_identifier = 'id'
        fields = ('name', 'email')

    class Meta:
        app_label = 'tests'


class ProductDimension(BaseDimension):

    class ReportingMeta:
        business_model = TestProduct
        unique_identifier = 'id'
        fields = ('name', 'price')

    class Meta:
        app_label = 'tests'


class OrderedProductFact(BaseFact):
    customer = DimensionForeignKey(CustomerDimension, on_delete=models.CASCADE)
    product = DimensionForeignKey(ProductDimension, on_delete=models.CASCADE)
    order_id = IntegerDescriptionField(computed=lambda instance: instance.order.id)
    created_on = DimensionForeignKey(DateDimension, computed=lambda instance: instance.order.created_on, related_name="orderedproduct_created_on", on_delete=models.CASCADE)
    hour_created_on = DimensionForeignKey(HourDimension, computed=lambda instance: instance.order.created_on, related_name="orderedproduct_hour_created_on", on_delete=models.CASCADE)
    ordered_on = DimensionForeignKey(DateDimension, computed=lambda instance: instance.order.ordered_on, related_name="orderedproduct_ordered_on", on_delete=models.CASCADE)
    hour_ordered_on = DimensionForeignKey(HourDimension, computed=lambda instance: instance.order.ordered_on, related_name="orderedproduct_hour_ordered_on", on_delete=models.CASCADE)

    @classmethod
    def delete_when(cls, instance):
        return instance.order.cancelled

    class ReportingMeta:
        business_model = TestOrderItem
        unique_identifier = 'id'
        fields = ('product', 'qty', 'total', 'order_id', 'customer', 'created_on', 'hour_created_on', 'hour_ordered_on', 'ordered_on')
        header_description = ['ID', 'Product', 'Qty', 'Total', 'Order ID''Created Date', 'Created Time', 'Customer', 'Ordered Date', 'Ordered Time']
        row_description = lambda row: [
            row._unique_identifier,
            row.product.name,
            row.qty,
            row.total,
            row.order_id,
            row.created_on.date,
            row.hour_created_on.time,
            row.customer.name,
            row.ordered_on.date,
            row.hour_ordered_on.time,
        ]

    class Meta:
        app_label = 'tests'


class OrderedFact(BaseFact):
    customer = DimensionForeignKey(CustomerDimension, on_delete=models.CASCADE)
    created_on = DimensionForeignKey(DateDimension, related_name="ordered_created_on", on_delete=models.CASCADE)
    hour_reated_on = DimensionForeignKey(HourDimension, alias='created_on', related_name="ordered_hour_created_on", on_delete=models.CASCADE)
    ordered_on = DimensionForeignKey(DateDimension, related_name="ordered_ordered_on", on_delete=models.CASCADE)
    hour_ordered_on = DimensionForeignKey(HourDimension, alias='ordered_on', related_name="ordered_hour_ordered_on", on_delete=models.CASCADE)

    @classmethod
    def delete_when(cls, instance):
        return instance.cancelled

    class ReportingMeta:
        business_model = TestOrder
        unique_identifier = 'id'
        fields = ('customer', 'created_on', 'hour_created_on', 'hour_ordered_on', 'ordered_on')
        header_description = ['ID', 'Created Date', 'Created Time', 'Customer', 'Ordered Date', 'Ordered Time']
        row_description = lambda row: [
            row._unique_identifier,
            row.created_on.date,
            row.hour_created_on.time,
            row.customer.name,
            row.ordered_on.date,
            row.hour_ordered_on.time,
        ]
        total = lambda filter_instance: filter_instance.qs.aggregate(total_count=models.Count('id'))

    class Meta:
        app_label = 'tests'
