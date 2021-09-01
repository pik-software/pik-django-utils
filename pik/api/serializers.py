from typing import Optional, Union
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django_restql.mixins import DynamicFieldsMixin
from model_utils.managers import InheritanceManager

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .lazy_field import LazyFieldHandlerMixIn
from .restql import DefaultRequestQueryParserMixin
# try:
#     from core.permitted_fields.api import PermittedFieldsSerializerMixIn
# except ImportError:
#     PermittedFieldsSerializerMixIn = None


def _normalize_label(label):
    if label:
        return label.capitalize()
    return label


class SettableNestedSerializerMixIn:
    default_error_messages = {
        'required': _('This field is required.'),
        'does_not_exist':
            _('Недопустимый uid "{uid_value}" - объект не существует.'),
        'incorrect_uid_type':
            _('Недопустимый uid. Ожидался uid, получен "{data_type}".'),
        'incorrect_type':
            _('Некорректный тип объекта. Ожидался "{expected_object_type}". '
              'Получен "{object_type}".'),
    }

    def run_validators(self, value):
        if not self.parent:
            return super().run_validators(value)
        return None

    def to_internal_value(self, request_data):
        if not self.parent:
            return super().to_internal_value(request_data)

        object_type = ""
        if hasattr(request_data, 'get'):  # request_data could be other types
            object_type = request_data.get('_type', None)

        model = self.Meta.model
        expected = [model._meta.model_name]  # noqa: protected-access

        # Check type through multi-table children too
        if isinstance(model.objects, InheritanceManager):
            expected.extend(model.objects.all()._get_subclasses_recurse(model))  # noqa: We just want to find all possible children

        if object_type not in expected:
            self.fail('incorrect_type',
                      expected_object_type=", ".join(expected),
                      object_type=object_type)
        uid_value = request_data.get('_uid')
        try:
            return model.objects.get(uid=uid_value)
        except model.DoesNotExist:
            self.fail('does_not_exist', uid_value=uid_value)
        except (TypeError, ValueError):
            self.fail('incorrect_uid_type', data_type=type(uid_value).__name__)

        return None


class StandardizedProtocolSerializer(serializers.ModelSerializer):
    guid = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    version = serializers.SerializerMethodField()

    @staticmethod
    def get_guid(obj) -> Optional[Union[UUID, str]]:
        if not hasattr(obj, 'uid'):
            if not hasattr(obj, 'pk'):
                return None
            return str(obj.pk)
        return obj.uid

    @staticmethod
    def get_type(obj) -> Optional[str]:
        return obj._meta.model_name  # noqa: protected-access

    @staticmethod
    def get_version(obj) -> Optional[int]:
        if not hasattr(obj, 'version'):
            return None
        return obj.version


class LabeledModelSerializerMixIn:
    """ Default DRF ModelSerializer has different nature than DRF Field

        1. DRF ModelSerializer does't handle labels and help_texts as expected.
        2. DRF ModelSerializer has 2 different behaviours:
            - initialized for direct use within viewset,
            - initialized and binded for use within other serializer as field.
        3. So label and help_text handling should be done during two stages:
            - `__init__()` for using within viewset,
            - `bind()` for use as field withing other serializer.

        This MixIn:
            - on `__init__()`:
                - sets label and help_text to model values if not provided,
                - saves `is_set`=True if provided;
            - on `bind()`:
                - sets parent model field fetched `label` and `help_text`
                values if `is_set`=`False`.
    """

    _label_is_set = False
    _help_text_is_set = False

    def __init__(self, *args, **kwargs):
        opts = self.Meta.model._meta

        if 'label' not in kwargs:
            kwargs['label'] = _normalize_label(opts.verbose_name)
        else:
            self._label_is_set = True

        if 'help_text' not in kwargs:
            kwargs['help_text'] = getattr(self.Meta.model(),
                                          '_help_text', None)
        else:
            self._help_text_is_set = True

        self.label_plural = _normalize_label(opts.verbose_name_plural)
        if 'label_plural' in kwargs:
            self.label_plural = kwargs.pop('label_plural')

        super().__init__(*args, **kwargs)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        if isinstance(parent, ModelSerializer):
            opts = parent.Meta.model._meta
            if not self._label_is_set:
                self.label = _normalize_label(opts.get_field(self.source)
                                              .verbose_name)
            if not self._help_text_is_set:
                self.help_text = opts.get_field(self.source).help_text


class ValidatedModelSerializerMixIn:
    """ Allows using model defined validators due to missing DRF clean
    handling """

    def validate(self, attrs):
        if not self.parent:
            errors = []
            validators = getattr(self.Meta.model, 'validators', ())
            for validator in validators:
                try:
                    validator(
                        attrs, self.instance, self.Meta.model,
                        serializers.ValidationError)
                except serializers.ValidationError as exc:
                    errors.append(exc.detail)
            if errors:
                raise serializers.ValidationError(
                    dict(zip(range(0, len(errors)), errors)))
        return super().validate(attrs)


class DynamicModelSerializerMixIn:
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    https://github.com/CarlosMart626/djangocon-2019/blob/master/five_minutes/five_minutes/serializers.py
    """

    def get_field_names(self, declared_fields, info) -> str:
        field_names = super().get_field_names(
            declared_fields, info)
        if self.dynamic_fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(self.dynamic_fields)
            excluded_field_names = set(field_names) - allowed
            field_names = tuple(x for x in field_names
                                if x not in excluded_field_names)
        return field_names

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' or 'read_only_fields'
        # arg up to the superclass
        self.dynamic_fields = kwargs.pop('fields', None)
        self.read_only_fields = kwargs.pop('read_only_fields', [])

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)


class StandardizedModelSerializer(
        DefaultRequestQueryParserMixin,
        DynamicFieldsMixin,
        LazyFieldHandlerMixIn,
        LabeledModelSerializerMixIn,
        SettableNestedSerializerMixIn,
        ValidatedModelSerializerMixIn,
        DynamicModelSerializerMixIn,
        StandardizedProtocolSerializer,
        # *((PermittedFieldsSerializerMixIn,)
        #   if PermittedFieldsSerializerMixIn else tuple())
):

    # we pass soft deleted logic here because drf-yasg can't find type of
    # `is_deleted` if it declared on parent's parent
    is_deleted = serializers.SerializerMethodField()

    @staticmethod
    def get_is_deleted(obj) -> bool:
        return bool(obj.deleted)
