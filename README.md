# opinionated-reporting
A reporting framework for that runs on django

My opinion is that a reporting system requires data to be normalized differently than an operational/transactional system
in order for either to remain performant. You can optimize operational systems in many ways that make them very fast. Often
these operations will make any attempt at reporting much slower. While optimizng for reporting can easily make your
operational system slow or difficult to maintain.

The goal of this application is to create a separated data structure optimized for reporting purposes. This frees you,
the developer, up to optimizing your application in any and every way you see fit. While your reporting system comes
for free and optimized. Creating that reporting system should be just as simple as serializing models, or writing
forms for you models. Making this simple to create allow you to focus on creating all the moments and events 
you are trying to report on (the harder it is, the fewer you'll want to track). In my opinion, track everything you
ever think you can want.

## Creating a reporting system with Opinionated Reporting
You will define specific "Facts" that represent a reportable moment in the lifecycle of your operational system.
That moment may be when a order moves from "in checkout" to "completed checkout". That moment may be when a price
on a SKU, or stock ticker, changes. Each of those moments are a different "Fact".

These facts will contain the necessary fields you are tracking. The fields will either be a quantitative value, or
a "Dimension" that is filterable. For instance, the total amount on an order is a quantitative value, while the Customer
that order belongs to (along with any and all of the indentifiable data for a customer) is a "Dimension".


## Example
If you had an `Order` model that looked roughly like this:
```python
class TestOrder(models.Model):
    customer = models.ForeignKey(TestCustomer)
    products = models.ManyToManyField(TestProduct, through=TestOrderItem)
    created_on = models.DateTimeField(auto_now_add=True)
    ordered_on = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    cancelled = models.BooleanField(default=False)
```

You would create an `OrderedFact` model that looks like this:
```python
class OrderedFact(BaseFact):
    customer = DimensionForeignKey(CustomerDimension)
    created_on = DimensionForeignKey(DateDimension, related_name="ordered_created_on")
    hour_created_on = DimensionForeignKey(HourDimension, alias='created_on', related_name="ordered_hour_created_on")
    ordered_on = DimensionForeignKey(DateDimension, related_name="ordered_ordered_on")
    hour_ordered_on = DimensionForeignKey(HourDimension, alias='ordered_on', related_name="ordered_hour_ordered_on")

    @classmethod
    def delete_when(cls, instance):
        return instance.cancelled

    class ReportingMeta:
        business_model = 'opinionated_reporting.tests.TestOrder'
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
```
