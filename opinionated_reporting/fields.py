from django.db import models
from . import base


class BaseDescriptionField(base.HandleFieldArgs):
    pass


class CharDescriptionField(BaseDescriptionField, models.CharField):
    pass


class DecimalDescriptionField(BaseDescriptionField, models.DecimalField):
    pass


class IntegerDescriptionField(BaseDescriptionField, models.CharField):
    pass


class DescriptionFieldWrapper(object):

    def __init__(self, field):
        self.field = field

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = value

    def __get__(self, instance, cls=None):
        if instance is None:  # unsure what case this handles
            return None
        return DescriptionFieldOperations(instance, self.field.name, self.field)


class DescriptionFieldOperations(object):

    def __init__(self, instance, name, field):
        self.value = instance.__dict__[name]
        self.name = name
        self.instance = instance
        self.field = field

    def to_python(self):
        return self.value

    def __repr__(self):
        return '{}: {}'.format(self.__class__.__name__, self.value)

    def value_from_instance(self, instance):
        val = None
        if self.field.computed:
            val = self.field.computed(instance)
        elif self.field.alias:
            val = getattr(instance, self.field.alias)
        else:
            val = getattr(instance, self.name)
        return val


class DimensionForeignKey(base.HandleFieldArgs, models.ForeignKey):
    """
    Has to check alias/computed during an update
    """
    pass
