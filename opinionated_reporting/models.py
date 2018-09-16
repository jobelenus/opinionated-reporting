import datetime
from django.db import models
from django.apps import apps
from django.conf import settings
from django.db import IntegrityError
from . import fields
import pytz


local_tz = pytz.timezone(settings.TIME_ZONE)


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
            reporting_model = getattr(reporting_meta, 'business_model', None)
            if not reporting_model:
                raise Exception('Must set `business_model` to define the model {} is reporting against'.format(new_class))
            elif isinstance(reporting_model, str):
                # XXX this doesn't work yet, models aren't loaded yet
                reporting_model = apps.get_model(reporting_model)

            reporting_fields = getattr(reporting_meta, 'fields', [])
            fields_to_create = list(filter(None, [field_name for field_name in reporting_fields if not hasattr(new_class, field_name)]))

            # add the fields defined in the metaclass
            for model_field in reporting_model._meta.fields:
                field_name = model_field.name
                handler = FieldHandler(model_field)
                if isinstance(model_field, models.ForeignKey):
                    continue  # FKs have to be manually linked with DimensionFK classes
                # add the unique identifer based on the type
                elif field_name == unique_field_name:
                    if not handler.is_valid_field_type:
                        raise Exception("Invalid field type declared as the unique identifier")
                    new_class.add_to_class('_unique_identifier', handler.model_field_class(**handler.field_kwargs))
                elif field_name not in fields_to_create:
                    continue
                else:
                    if handler.is_valid_field_type:
                        new_class.add_to_class(field_name, handler.model_field_class(**handler.field_kwargs))
        return new_class


class FieldHandler(object):

    def __init__(self, model_field):
        self.model_field = model_field

    @property
    def is_valid_field_type(self):
        if (isinstance(self.model_field, models.DateTimeField) or isinstance(self.model_field, models.DateField) or
                isinstance(self.model_field, models.IntegerField) or isinstance(self.model_field, models.BigIntegerField) or
                isinstance(self.model_field, models.PositiveIntegerField) or isinstance(self.model_field, models.FloatField) or
                isinstance(self.model_field, models.PositiveSmallIntegerField) or isinstance(self.model_field, models.SmallIntegerField) or
                isinstance(self.model_field, models.TextField) or isinstance(self.model_field, models.AutoField) or
                isinstance(self.model_field, models.SlugField) or isinstance(self.model_field, models.DecimalField) or
                isinstance(self.model_field, models.CharField)):
            return True
        else:  # we aren't handling this field type
            return False

    @property
    def model_field_class(self):
        """
        Cannot have two AutoFields on a model, so turn any AutoField into a PositiveIntegerField
        """
        return models.PositiveIntegerField if isinstance(self.model_field, models.AutoField) else self.model_field.__class__

    @property
    def field_kwargs(self):
        kwargs = {}
        if isinstance(self.model_field, models.SlugField):
            kwargs.update({
                'max_length': self.model_field.max_length,
                'allow_unicode': self.model_field.allow_unicode
            })
        elif isinstance(self.model_field, models.DecimalField):
            kwargs.update({
                'max_digits': self.model_field.max_digits,
                'decimal_places': self.model_field.decimal_places
            })
        elif isinstance(self.model_field, models.CharField):
            kwargs.update({'max_length': self.model_field.max_length})
        return kwargs


def assert_instance(fn):
    # actually, cls is a class or instance
    def wrapped(cls, instance):
        assert isinstance(instance, cls.ReportingMeta.business_model), "{} is not a {}".format(instance, cls.ReportingMeta.business_model)
        fn(cls, instance)
    return wrapped


def datetime_is_naive(d):
    return True if d.tzinfo is None or d.tzinfo.utcoffset(d) is None else False


class UpdatingModel(models.Model, metaclass=UpdatingModelMeta):  # NOQA
    # note: there is an implicit `_unique_identifier` field here that comes from the metaclass
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
        cls._default_manager.filter(_unique_identifier=unique_id).update(_is_dirty=True)

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
            fact._record_update(instance)
            fact.save()

    @classmethod
    @assert_instance
    def get_reporting_fact_id(cls, instance):
        return getattr(instance, cls.ReportingMeta.unique_identifier)

    @classmethod
    def get_reporting_fact(cls, instance):
        unique_id = cls.get_reporting_fact_id(instance)
        try:
            return cls._default_manager.get(_unique_identifier=unique_id)
        except cls.DoesNotExist:
            return cls(_is_dirty=True, _unique_identifier=unique_id)

    @classmethod
    def needs_update(cls, instance):
        fact = cls.get_reporting_fact(instance)
        return fact._is_dirty

    @assert_instance
    def _record_update(self, instance):
        if self._is_frozen:
            return
        for field in self._meta.fields:
            field_name = field.name
            if field_name.startswith('_') or field.primary_key:  # ignore my internal fields
                continue
            if isinstance(field, fields.HandleFieldArgs):
                val = getattr(instance, field_name)
                if hasattr(field, 'value_from_instance'):
                    val = field.value_from_instance(instance)
                if isinstance(field, fields.DimensionForeignKey):
                    # Store dates and times from tz-aware datetimes in the setting defined local tz
                    if issubclass(field.related_model, DateDimension):
                        if isinstance(val, datetime.date) or isinstance(val, datetime.datetime):
                            if not datetime_is_naive(val):
                                val = val.astimezone(local_tz)
                            if hasattr(val, 'date'):
                                val = val.date()
                            self.__dict__[field_name] = field.related_model._default_manager.get(date=val)
                    elif issubclass(field.related_model, HourDimension):
                        if isinstance(val, datetime.datetime):
                            if not datetime_is_naive(val):
                                val = val.astimezone(local_tz)
                            val = datetime.time(hour=val.hour, minute=0)
                        elif isinstance(val, datetime.time):
                            val = datetime.time(hour=val.hour, minute=0)
                        self.__dict__[field_name] = field.related_model._default_manager.get(time=val)
                    else:
                        # TODO: Update the "None" value to the corresponding None dimension record
                        if val:
                            dim_unique_id = getattr(val, field.related_model.ReportingMeta.unique_identifier)
                            if dim_unique_id:
                                try:
                                    self.__dict__[field_name] = field.related_model._default_manager.get(_unique_identifier=dim_unique_id)
                                except field.related_model.DoesNotExist:
                                    self.__dict__[field_name] = None
                            else:
                                self.__dict__[field_name] = None
                        else:
                            self.__dict__[field_name] = None
                else:
                    self.__dict__[field_name] = val
            else:
                self.__dict__[field_name] = val
                # TODO: clean up this deep nesting mess

    class Meta:
        abstract = True


class BaseDimension(UpdatingModel):

    @classmethod
    def init_dimension(cls):
        # TODO: mgmt command to run init_dimension on all models
        # don't do anything if you're an abstract model
        test_instance = cls()
        if not test_instance._meta.abstract:
            empty_record = getattr(cls.ReportingMeta, 'empty_label', None)
            if empty_record:
                try:
                    kwargs = {empty_record[0]: empty_record[1], '_unique_identifier': 0}
                    print(" -INIT- ", cls, kwargs)
                    cls.objects.create(**kwargs)
                except IntegrityError:
                    pass

    class Meta:
        abstract = True


class DateDimension(models.Model):
    """
    NOTE: DateDimension does not inherit from BaseDimension
    It doesn't do this because it is not an `UpdatingModel` from
    a corresponding business model
    """
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

    @classmethod
    def init_dimension(cls):
        raise NotImplementedError  # see initilization below

    @classmethod
    def init_dimension_by_range(cls, start, end):
        # NOTE: not calling super on purpose here
        assert isinstance(start, datetime.date), "`start` must be a python date object"
        assert isinstance(end, datetime.date), "`end` must be a python date object"

        def _date_range():
            while start <= end:
                yield start
                start += datetime.timedelta(days=1)

        for date in _date_range():
            isocalendar = date.isocalendar()
            kwargs = {
                'date': date,
                'month_format': cls.create_month_format(date),
                'quarter_format': cls.create_quarter_format(date),
                'isoformat': date.isoformat(),
                'day_of_week': date.weekday(),
                'week_number': isocalendar[1],
                'week_number_year': '%s %s' % (isocalendar[1], isocalendar[0])
            }
            try:
                cls.objects.create(**kwargs)
            except IntegrityError:
                pass

    @classmethod
    def create_month_format(cls, date):
        return date.strftime(cls.MONTH_FMT)

    @classmethod
    def create_quarter_format(cls, date):
        return cls.QUARTER_FMT % ({
            1: 1, 2: 1, 3: 1,
            4: 2, 5: 2, 6: 2,
            7: 3, 8: 3, 9: 3,
            10: 4, 11: 4, 12: 4
        }.get(date.month), date.strftime('%y'))


class HourDimension(models.Model):
    """
    NOTE: DateDimension does not inherit from BaseDimension
    It doesn't do this because it is not an `UpdatingModel` from
    a corresponding business model
    """
    time = models.TimeField(unique=True)
    us_format = models.CharField(max_length=16)

    @classmethod
    def init_dimension(cls):
        # NOTE: not calling super on purpose here
        for i in range(0, 24):
            t = datetime.time(hour=i, minute=0)
            try:
                cls.objects.create(time=t, us_format=t.strftime("%I:%M%p"))
            except IntegrityError:
                pass


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
