from django.apps import apps
from opinionated_reporting import models

all_models = apps.get_models()


def _find_reporting_from(model_instance):
    klasses = []
    for model in all_models:
        if isinstance(models.BaseFact, model):
            reporting_meta = getattr(model, 'ReportingMeta', None)
            if reporting_meta:
                reporting_model = getattr(reporting_meta, 'model', None)
                if reporting_model:
                    klasses.append(reporting_model)
    return klasses


def dirty_reporting_on_save(sender, instance, created, *args, **kwargs):
    klasses = _find_reporting_from(instance)
    for klass in klasses:
        if not created:
            klass.mark_dirty(instance)
        else:
            fact = klass.get_reporting_fact(instance)
            fact.save()


def update_reporting_on_save(sender, instance, created, *args, **kwargs):
    klass = _find_reporting_from(instance)
    klass.record_update(instance, force=True)
