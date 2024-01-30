import importlib
from functools import partial

from django.db.models.signals import m2m_changed
from django.db import models
from simple_history import exceptions
from simple_history.models import HistoricalRecords
from simple_history.manager import HistoryDescriptor



class PikHistoricalRecords(HistoricalRecords):


    def create_history_model(self, model, inherited):
        if getattr(model, '_is_history_enabled', True):
            super().create_history_model(model, inherited)

    def finalize(self, sender, **kwargs):
        inherited = False
        if self.cls is not sender:  # set in concrete
            inherited = self.inherit and issubclass(sender, self.cls)
            if not inherited:
                return  # set in abstract

        if hasattr(sender._meta, "simple_history_manager_attribute"):
            raise exceptions.MultipleRegistrationsError(
                "{}.{} registered multiple times for history tracking.".format(
                    sender._meta.app_label, sender._meta.object_name
                )
            )
        history_model = self.create_history_model(sender, inherited)
        if not history_model:
            return

        if inherited:
            # Make sure history model is in same module as concrete model
            module = importlib.import_module(history_model.__module__)
        else:
            module = importlib.import_module(self.module)
        setattr(module, history_model.__name__, history_model)

        # The HistoricalRecords object will be discarded,
        # so the signal handlers can't use weak references.
        models.signals.post_save.connect(
            self.post_save, sender=sender, weak=False)
        models.signals.post_delete.connect(
            self.post_delete, sender=sender, weak=False)

        m2m_fields = self.get_m2m_fields_from_model(sender)

        for field in m2m_fields:
            m2m_changed.connect(
                partial(self.m2m_changed, attr=field.name),
                sender=field.remote_field.through,
                weak=False,
            )

        descriptor = HistoryDescriptor(history_model)
        setattr(sender, self.manager_name, descriptor)
        sender._meta.simple_history_manager_attribute = self.manager_name

        for field in m2m_fields:
            m2m_model = self.create_history_m2m_model(
                history_model, field.remote_field.through
            )
            self.m2m_models[field] = m2m_model

            setattr(module, m2m_model.__name__, m2m_model)

            m2m_descriptor = HistoryDescriptor(m2m_model)
            setattr(history_model, field.name, m2m_descriptor)


class Historized(models.Model):
    history = PikHistoricalRecords(inherit=True)

    class Meta:
        abstract = True
