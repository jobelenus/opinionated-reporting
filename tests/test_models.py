import datetime
from django.test import TestCase
from django.db import transaction
from opinionated_reporting import models as opr_models
from . import models

PRICE = 5.00
QTY = 2
TAX = 0.50


class TestModels(TestCase):

    def setUp(self):
        opr_models.HourDimension.objects.all().delete()
        with transaction.atomic():
            opr_models.HourDimension.init_dimension()

        opr_models.DateDimension.objects.all().delete()
        with transaction.atomic():
            opr_models.DateDimension.init_dimension_by_range(datetime.date.today() - datetime.timedelta(days=3), datetime.date.today() + datetime.timedelta(days=3))

        with transaction.atomic():
            models.CustomerDimension.init_dimension()
        with transaction.atomic():
            models.ProductDimension.init_dimension()

        self.product = models.TestProduct.objects.create(**{
            'name': 'Widget',
            'price': PRICE
        })
        self.customer = models.TestCustomer.objects.create(**{
            'email': 'foo@bar.com',
            'name': 'Foo Bar'
        })
        self.order = models.TestOrder.objects.create(**{
            'customer': self.customer,
            'total': PRICE * QTY,
            'ordered_on': datetime.datetime.now()
        })
        models.TestOrderItem.objects.create(**{
            'order': self.order,
            'product': self.product,
            'quantity': QTY,
            'total': PRICE * QTY
        })

    def tearDown(self):
        self.order.delete()
        self.product.delete()
        self.customer.delete()

    def test_creation(self):
        fact = models.OrderedFact.get_reporting_fact(self.order)
        self.assertGreater(models.OrderedFact.objects.all().count(), 0)
        self.assertEquals(fact._is_dirty, True)

    def test_dirty(self):
        models.OrderedFact.record_update(self.order)
        self.order.tax = TAX
        self.order.total += TAX
        self.order.save()
        fact = models.OrderedFact.get_reporting_fact(self.order)
        self.assertEquals(fact._is_dirty, True)

    def test_update(self):
        models.OrderedFact.record_update(self.order)
        original_total = self.order.total
        fact = models.OrderedFact.get_reporting_fact(self.order)
        self.assertEquals(fact.total, original_total)
        self.order.tax = TAX
        self.order.total += TAX
        new_total = self.order.total
        self.order.save()
        models.OrderedFact.record_update(self.order)
        fact = models.OrderedFact.get_reporting_fact(self.order)
        self.assertEquals(fact.total, new_total)

    def test_delete(self):
        models.OrderedFact.get_reporting_fact(self.order)
        self.assertGreater(models.OrderedFact.objects.all().count(), 0)
        self.order.cancelled = True
        self.order.save()
        # cancelled orders are removed from reporting
        models.OrderedFact.record_update(self.order)
        self.assertEquals(models.OrderedFact.objects.all().count(), 0)

    def test_freeze(self):
        models.OrderedFact.get_reporting_fact(self.order)
        self.assertGreater(models.OrderedFact.objects.all().count(), 0)
        models.OrderedFact.freeze(self.order)
        # reporting should not be able to be changed once frozen
        self.order.cancelled = True
        self.order.save()
        models.OrderedFact.record_update(self.order)
        self.assertGreater(models.OrderedFact.objects.all().count(), 0)
