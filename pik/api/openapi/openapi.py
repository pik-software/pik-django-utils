import inspect

from django.conf import settings
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from django.forms.utils import pretty_name
from django_filters import OrderingFilter
from django_restql.mixins import DynamicFieldsMixin
from rest_framework import serializers
from rest_framework.fields import (
    ChoiceField, JSONField, MultipleChoiceField,
    SerializerMethodField, _UnvalidatedField, )
from rest_framework.serializers import ModelSerializer
from rest_framework.schemas.openapi import AutoSchema, SchemaGenerator
# TODO: klimenkoas: Drop `drf_yasg` dependency
from drf_yasg.inspectors.field import (
    get_basic_type_info_from_hint, typing, inspect_signature, )
from drf_yasg.utils import (
    force_real_str, field_value_to_representation, filter_none, )
from pik.api.openapi.reference import (
    ReferenceAutoSchema, ReferenceSchemaGenerator)

from .utils import deepmerge


FIELD_MAPPING = (
    ('title', 'label', lambda x: force_real_str(x).strip().capitalize()),
    ('description', 'help_text', force_real_str)
)


SERIALIZER_FIELD_MAPPING = FIELD_MAPPING + (
    ('x-title-plural', 'label_plural', force_real_str),
)


class MethodFieldHintRequired(Exception):
    pass


class RedundantSchemaKeys(Exception):
    pass


class TypedSerializerAutoSchema(AutoSchema):
    """Adds enum for `serializer._type`"""
    TYPE_FIELD = 'type'

    def map_serializer(self, serializer):
        schema = super().map_serializer(serializer)
        properties = schema['properties']
        type_field = serializer.fields.get(self.TYPE_FIELD)
        has_typefield = (
            isinstance(serializer, ModelSerializer)
            and isinstance(type_field, SerializerMethodField)
            and self.TYPE_FIELD in properties)
        if has_typefield:
            type_name = type_field.to_representation(serializer.Meta.model())
            if type_name:
                properties[self.TYPE_FIELD]['enum'] = [type_name]
        return schema


class ModelSerializerFieldsAutoSchema(AutoSchema):
    """ Adds serializers title, description and x-title-plural  """

    def map_serializer(self, serializer):
        schema = super().map_serializer(serializer)
        for dst, src, method in SERIALIZER_FIELD_MAPPING:
            value = getattr(serializer, src, None)
            if value is not None:
                schema[dst] = method(value)
        return schema


class ListFieldAutoSchema(AutoSchema):
    """ Provides correct choices limited list handling

    DRF BUG workaround
    https://github.com/encode/django-rest-framework/issues/7023
    """
    def map_field(self, field):
        if isinstance(field, serializers.ListField):
            mapping = {
                'type': 'array',
                'items': {},
            }
            if not isinstance(field.child, _UnvalidatedField):
                mapping['items'] = self.map_field(field.child)
            return mapping
        return super().map_field(field)


class EnumNamesAutoSchema(AutoSchema):
    """ Adds enumNames for choice and ordering fields """

    def map_field(self, field):
        schema = super().map_field(field)
        if isinstance(field, ChoiceField):
            enum_values = []
            for choice in field.choices.values():
                if isinstance(field, MultipleChoiceField):
                    choice = field_value_to_representation(field, [choice])[0]
                else:
                    choice = field_value_to_representation(field, choice)

                enum_values.append(choice)
            if enum_values:
                schema['x-enumNames'] = enum_values

        return schema

    def get_model_field_label(self, field_name):
        desc = False
        model = self.view.serializer_class.Meta.model
        if field_name.startswith('-'):
            desc = True
            field_name = field_name[1:]

        try:
            model_field = model._meta.get_field(field_name)
            label = (model_field.verbose_name if model_field.verbose_name
                     else field_name)
        except FieldDoesNotExist:
            label = field_name

        label = pretty_name(label)
        if desc:
            label = label + _(' (по убыванию)')

        return label

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        parameters = operation['parameters']

        ordering_field_names = [
            field_name for field_name, filter
            in self.view.filterset_class.declared_filters.items()
            if isinstance(filter, OrderingFilter)]

        for parameter in parameters:
            if parameter['name'] in ordering_field_names:
                schema = parameter['schema']
                schema['x-enumNames'] = [
                    self.get_model_field_label(val) for val in schema['enum']]

        return operation


class DeprecatedFieldAutoSchema(AutoSchema):
    """ Fetches serializer deprecation status from serializer and parent """

    def map_serializer(self, serializer):
        schema = super().map_serializer(serializer)

        parent_meta = getattr(serializer.parent, 'Meta', None)
        deprecated = getattr(parent_meta, 'deprecated_fields', {})
        is_deprecated_as_field = deprecated.get(serializer.field_name, False)

        is_deprecated = getattr(getattr(serializer, 'Meta', None),
                                'deprecated', False)

        if is_deprecated_as_field or is_deprecated:
            schema['deprecated'] = True
        return schema


class DeprecatedSerializerAutoSchema(AutoSchema):
    """ Fetches fields and serializer deprecation status from parent serializer
    `Meta` class """

    def map_field(self, field):
        schema = super().map_field(field)
        _meta = getattr(field.parent, 'Meta', None)
        deprecated = getattr(_meta, 'deprecated_fields', {})
        is_deprecated = deprecated.get(field.field_name, False)
        if is_deprecated:
            schema['deprecated'] = is_deprecated
        return schema


class FieldMappingAutoSchema(AutoSchema):
    """ Fetches field properties from serializer

    Default DRF openapi AutoSchema ignores Fields titles."""

    def map_field(self, field):
        schema = super().map_field(field)
        for dst, src, method in FIELD_MAPPING:
            value = getattr(field, src, None)
            if value is not None:
                schema[dst] = method(value)
        return schema


class SerializerMethodFieldAutoSchema(AutoSchema):
    """ Provides `SerializerMethodField` property types by
    python typing introspection """

    # TODO: klimenko add Serializer handling inside SerializerMethodField
    def map_field(self, field):
        schema = super().map_field(field)
        supports_signing = typing and inspect_signature
        if isinstance(field, SerializerMethodField) and supports_signing:
            method = getattr(field.parent, field.method_name)
            hint_class = inspect_signature(method).return_annotation
            if (not inspect.isclass(hint_class)
                    and hasattr(hint_class, '__args__')):
                hint_class = hint_class.__args__[0]  # noqa: protected-access
            if (inspect.isclass(hint_class)
                    and not issubclass(hint_class, inspect._empty)):  # noqa: protected-access
                type_info = get_basic_type_info_from_hint(hint_class)
                schema.update(filter_none(type_info))
            else:
                raise MethodFieldHintRequired(
                    f'{field.parent.__class__.__name__}.{method.__name__}'
                    f' type hint missing!')
        return schema


class JSONFieldAutoSchema(AutoSchema):
    """ Provides `JSONField` schema """

    def map_field(self, field):
        schema = super().map_field(field)
        if isinstance(field, JSONField):
            schema['type'] = 'object'
        return schema


class ListFiltersOnlyAutoSchema(AutoSchema):
    """ Removes filters for non list view actions

        Overriding default DRF
    """

    def allows_filters(self, path, method):
        result = super().allows_filters(path, method)
        return result and getattr(self.view, 'action', '') == "list"


class CustomizableSerializerAutoSchema(AutoSchema):
    """ Schema inspector with inplace overriding support """

    def map_serializer(self, serializer):
        result = super().map_serializer(serializer)
        if hasattr(serializer, 'update_schema'):
            if callable(serializer.update_schema):
                result = serializer.update_schema(result)
            else:
                result = deepmerge(serializer.update_schema, result)
        return result


class OperationSummaryAutoSchema(AutoSchema):
    SUMMARY_FORMATS = (
        ('list', _('Список объектов {serializer.label_plural}')),
        ('retrieve', _('Получить объект {serializer.label}')),
        ('create', _('Создать объект {serializer.label}')),
        ('update', _('Заменить объект {serializer.label}')),
        ('partial_update', _('Частично изменить объект {serializer.label}')),
        ('destroy', _('Удалить объект {serializer.label}')),
    )

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        if not hasattr(self.view, 'get_serializer'):
            return operation
        serializer = self.view.get_serializer(method, path)
        for prefix, summary in self.SUMMARY_FORMATS:
            if operation['operationId'].startswith(prefix):
                operation['summary'] = summary.format(serializer=serializer)
        return operation


class OperationSerializerDescriptionAutoSchema(AutoSchema):
    """Fetches operation description from serializer help_text if missing"""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        if not hasattr(self.view, 'get_serializer'):
            return operation
        serializer = self.view.get_serializer(method, path)
        if (not operation.get('description')
                and serializer and serializer.help_text):
            operation['description'] = serializer.help_text
        return operation


class RESTQLOperationParametersAutoSchema(AutoSchema):
    """Limit response properties documentation"""

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        if issubclass(self.view.serializer_class, DynamicFieldsMixin):
            operation['parameters'].append({
                "name": 'query',
                "in": "query",
                "required": False,
                "description": 'Limit response properties',
                'schema': {
                    'type': 'string',  # TODO: integer, pattern, ...
                    'example': '{field1,field2{subfield1, subfield2}}'
                },
            })
        return operation


class MethodTagAutoSchema(AutoSchema):
    def get_tags(self, path, method):
        if hasattr(self.view, 'serializer_class'):
            tags = (self.view.serializer_class.Meta.model._meta.verbose_name, )
            return tags
        return super().get_tags(path, method)


class CustomizableViewSchemaMixIn:
    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        if hasattr(self.view, 'update_schema'):
            operation = self._update_operation(operation)
        return operation

    def _update_operation(self, operation):
        if callable(self.view.update_schema):
            return self.view.update_schema(operation)
        return deepmerge(self.view.update_schema, operation)


class PIKAutoSchema(
        CustomizableViewSchemaMixIn,
        CustomizableSerializerAutoSchema,
        JSONFieldAutoSchema,
        ListFieldAutoSchema,
        ReferenceAutoSchema,
        TypedSerializerAutoSchema,
        EnumNamesAutoSchema,
        DeprecatedFieldAutoSchema,
        DeprecatedSerializerAutoSchema,
        ModelSerializerFieldsAutoSchema,
        FieldMappingAutoSchema,
        ListFiltersOnlyAutoSchema,
        OperationSummaryAutoSchema,
        OperationSerializerDescriptionAutoSchema,
        RESTQLOperationParametersAutoSchema,
        MethodTagAutoSchema,
        SerializerMethodFieldAutoSchema):
    pass


class EntitiesViewSchemaGenerator(SchemaGenerator):
    @staticmethod
    def _get_tags(schema):
        return set(
            tag
            for path in schema.get('paths', ()).values()
            for operation in path.values()
            for tag in operation.get('tags', ())
        )

    def get_schema(self, *args, **kwargs):
        schema = super().get_schema(*args, **kwargs)
        if schema is not None:
            schema['x-tagGroups'] = [
                {'name': gettext('Сущности'),
                 'tags': sorted(self._get_tags(schema))},
            ]
        return schema


class OpenIDSchemaGenerator(SchemaGenerator):
    def get_schema(self, *args, **kwargs):
        schema = super().get_schema(*args, **kwargs)

        endpoint = getattr(settings, 'OIDC_PIK_ENDPOINT', None)
        if not endpoint:
            return schema

        schema.setdefault('components', {})
        schema['components']['securitySchemes'] = {
            'OpenIDConnect': {
                'type': 'openIdConnect',
                'openIdConnectUrl':
                    f'{endpoint}/.well-known/openid-configuration'
            }
        }

        schema.setdefault('paths', {})
        for path in schema['paths'].values():
            for operation in path.values():
                operation['security'] = ({'OpenIDConnect': ()},)

        return schema


class PIKSchemaGenerator(
        OpenIDSchemaGenerator,
        EntitiesViewSchemaGenerator,
        ReferenceSchemaGenerator):
    pass
