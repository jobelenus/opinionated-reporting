from django.db import models


class UpdatingModelMeta(models.base.ModelBase):
    """
    Looks at ReportingMeta model, unique_identifier, and fields
    to create the necessary model fields
    """

    def __new__(cls, name, bases, attrs, **kwargs):
        new_class = super().__new__(cls, name, bases, attrs, **kwargs)

        test_inst = new_class()  # need an instance to check for abstract
        if not test_inst._meta.abstract:  # b/c testing new_class.Meta.abstract is always False, per docs
            reporting_meta = getattr(new_class, 'ReportingMeta', None)
            if not reporting_meta:
                raise Exception('Create a `ReportingMeta` inner class on {}'.format(new_class))
            unique_field_name = getattr(reporting_meta, 'unique_identifier', None)
            if not unique_field_name:
                raise Exception('Must set `unique_field_name` to a field on the reporting model that defines uniqueness (usually ID) for {}'.format(new_class))
            reporting_model = getattr(reporting_meta, 'model', None)
            if not reporting_model:
                raise Exception('Must set `model` to define the model {} is reporting against'.format(new_class))

            # add the fields defined in the metaclass
            for field_name in reporting_model.fields:
                if not hasattr(new_class, field_name):  # i could already have this if its been manually defined
                    for model_field in reporting_model._meta.fields:
                        if isinstance(model_field, models.ForeignKey):
                            continue  # FKs have to be manually linked with DimensionFK classes
                        else:
                            add_name = '_unique_identifier' if field_name == unique_field_name else field_name
                            kwargs = {}
                            if (isinstance(model_field, models.DateTimeField) or isinstance(model_field, models.DateField) or
                                    isinstance(model_field, models.IntegerField) or isinstance(model_field, models.BigIntegerField) or
                                    isinstance(model_field, models.PositiveIntegerField) or isinstance(model_field, models.FloatField) or
                                    isinstance(model_field, models.PositiveSmallIntegerField) or isinstance(model_field, models.SmallIntegerField) or
                                    isinstance(model_field, models.TextField)):
                                pass  # no kwargs to handle here
                            elif isinstance(model_field, models.SlugField):
                                kwargs.update({
                                    'max_length': model_field.max_length,
                                    'allow_unicode': model_field.allow_unicode
                                })
                            elif isinstance(model_field, models.DecimalField):
                                kwargs.update({
                                    'max_digits': model_field.max_digits,
                                    'decimal_places': model_field.decimal_places
                                })
                            elif isinstance(model_field, models.CharField):
                                kwargs.update({'max_length': model_field.max_length})
                            else:  # we aren't handling this field type
                                continue
                            new_class.add_to_class(add_name, model_field.__class__(**kwargs))


def assert_instance(fn):
    # actually, cls is a class or instance
    def wrapped(cls, instance):
        assert isinstance(instance, cls.ReportingMeta.model), "{} is not a {}".format(instance, cls.ReportingMeta.model)
    return wrapped


class UpdatingModel(models.Model, metaclass=UpdatingModelMeta):  # NOQA
    # note: there is an implicit `_unique_identifier` field here
    _is_dirty = models.BooleanField(default=False)  # updated via signals from the originating model
    _is_frozen = models.BooleanField(default=False)  # will not allow changes or deletions (e.g. archived if underlying data changes)

    @classmethod
    def freeze(cls, instance):
        fact = cls.get_reporting_fact(instance)
        fact._is_frozen = True
        fact.save()

    @classmethod
    def mark_dirty(cls, instance):
        unique_id = cls.get_reporting_fact_id(instance)
        cls.ReportingMeta.model._default_manager.filter(_unique_identifier=unique_id).update(_is_dirty=True)

    @classmethod
    def record_update(cls, instance, force=False):
        fact = cls.get_reporting_fact(instance)
        if fact._is_frozen:
            return  # refuse to make any changes

        if hasattr(cls, 'delete_when') and callable(cls.delete_when):
            if cls.delete_when(instance):
                if fact.id:  # may not be saved yet
                    fact.delete()
                    return

        if fact._is_dirty or force:
            fact._record_update()
            fact.save()

    @classmethod
    @assert_instance
    def get_reporting_fact_id(cls, instance):
        cls.check_instance()
        return getattr(instance, cls.ReportingMeta.unique_identifier)

    @classmethod
    @assert_instance
    def get_reporting_fact(cls, instance):
        unique_id = cls.get_reporting_fact_id(instance)
        try:
            return cls.ReportingMeta.model._default_manager.get(_unique_identifier=unique_id)
        except cls.ReportingMeta.model.DoesNotExist:
            return cls.ReportingMeta.model(_is_dirty=True, _unique_identifier=unique_id)

    @classmethod
    def needs_update(cls, instance):
        fact = cls.get_reporting_fact(instance)
        return fact._is_dirty

    @assert_instance
    def _record_update(self, instance):
        if self._is_frozen:
            return
        for field_name in self.ReportingMeta.fields:
            field = getattr(self, field_name)
            if isinstance(field, HandleFieldArgs):
                val = field.value_from_instance(instance)
                if isinstance(field, DimensionForeignKey):
                    # TODO, determine what to do with TZ regarding dates and times
                    # Basic: store dates and times from tz-aware datetimes in the setting defined local tz
                    # Advanced: ???
                    if isinstance(field.related_model, DateDimension):
                        pass
                    elif isinstance(field.related_model, TimeDimension):
                        pass
                    else:
                        # TODO: handle "none" dimensions for when FK isn't set
                        self.__dict__[field_name] = field.related_model._default_manager.get(_unique_identifier=val)
                else:
                    self.__dict__[field_name] = val
            else:
                self.__dict__[field_name] = getattr(instance, field_name)

    class Meta:
        abstract = True


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
        setattr(cls, self.name, DescriptionFieldWrapper(self))


class BaseDimension(UpdatingModel):
    # TODO: always have a "None" record populated

    class Meta:
        abstract = True


class DateDimension(BaseDimension):
    QUARTER_FMT = "Q%i %s"
    MONTH_FMT = "%b %Y"
    DAY_NONE = -1
    DAY_MONDAY = 0
    DAY_TEUSDAY = 1
    DAY_WEDNESDAY = 2
    DAY_THURSDAY = 3
    DAY_FRIDAY = 4
    DAY_SATURDAY = 5
    DAY_SUNDAY = 6
    WEEK_DAYS = (
        (DAY_NONE, "None"),
        (DAY_SUNDAY, "Sunday"),
        (DAY_MONDAY, "Monday"),
        (DAY_TEUSDAY, "Tuesday"),
        (DAY_WEDNESDAY, "Wednesday"),
        (DAY_THURSDAY, "Thursday"),
        (DAY_FRIDAY, "Friday"),
        (DAY_SATURDAY, "Saturday"),
    )
    # we don't want "None" in there
    FILTER_WEEK_DAYS = (
        (DAY_SUNDAY, "Sunday"),
        (DAY_MONDAY, "Monday"),
        (DAY_TEUSDAY, "Tuesday"),
        (DAY_WEDNESDAY, "Wednesday"),
        (DAY_THURSDAY, "Thursday"),
        (DAY_FRIDAY, "Friday"),
        (DAY_SATURDAY, "Saturday"),
    )
    date = models.DateField(db_index=True, unique=True, null=True, blank=True)
    isoformat = models.CharField(max_length=12)
    quarter_format = models.CharField(max_length=7, db_index=True)
    month_format = models.CharField(help_text="MON YEAR", max_length=8, db_index=True)
    day_of_week = models.IntegerField(default=DAY_NONE, choices=WEEK_DAYS)
    week_number = models.IntegerField(default=0)  # 0-53
    week_number_year = models.CharField(default='', max_length=10)  # "%d %d" % (0-53, 2006-2020)

    @staticmethod
    def create_quarter_format(date):
        return DateDimension.QUARTER_FMT % ({
            1: 1, 2: 1, 3: 1,
            4: 2, 5: 2, 6: 2,
            7: 3, 8: 3, 9: 3,
            10: 4, 11: 4, 12: 4
        }.get(date.month), date.strftime('%y'))


class HourDimension(BaseDimension):
    time = models.TimeField(unique=True)
    us_format = models.CharField(max_length=16)


class BaseFact(UpdatingModel):

    @classmethod
    def delete_when(self, instance):
        """
        Override and return true when you want to test to remove
        a record from reporting
        """
        return False

    class Meta:
        abstract = True
