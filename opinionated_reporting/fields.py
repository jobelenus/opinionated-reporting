from django.db import models


class HandleFieldArgs(object):

    def __init__(self, *args, **kwargs):
        for kwarg in ['alias', 'computed']:
            setattr(self, kwarg, kwargs.get(kwarg, None))
            if kwarg in list(kwargs.keys()):
                del kwargs[kwarg]

        # computed must be a callable
        if hasattr(self, 'computed'):
            if not callable(self.computed):
                self.computed = None
        super().__init__(*args, **kwargs)

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, name, DescriptionFieldWrapper(self))


class BaseDescriptionField(HandleFieldArgs):
    pass


class CharDescriptionField(BaseDescriptionField, models.CharField):
    pass


class DecimalDescriptionField(BaseDescriptionField, models.DecimalField):
    pass


class IntegerDescriptionField(BaseDescriptionField, models.IntegerField):
    pass


class DescriptionFieldWrapper(object):

    def __init__(self, field):
        self.field = field

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = value

    def __get__(self, instance, cls=None):
        if instance is None:  # Accesing descriptor on the class
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

    def __int__(self):
        return int(self.value)

    def __float__(self):
        return float(self.value)

    def __str__(self):
        return str(self.value)

    def __eq__(self, other):
        return True if other == self.to_python() else False

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


class DimensionForeignKey(models.ForeignKey):
    """
    Has to check for `opr_get_XXX` during an update
    """
    def __init__(self, *args, **kwargs):
        """
        All foreign keys need to be nullable in order to create an initial
        dirty record that has only a unique_identifier
        """
        if not kwargs.get('null', False):
            raise Exception('You must pass null=True for {}'.format(self))
        super().__init__(*args, **kwargs)
