from functools import reduce
from operator import or_

from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from rest_framework.fields import Field
from rest_framework.serializers import ModelSerializer, SerializerMetaclass


class LazySerializerRegistrationConflict(Exception):
    pass


class LazySerializerNotFound(Exception):
    pass


class LazyField(Field):
    """ Lazy placeholder which is replaced  with instance located by its'
        `path` by `LazyFieldHandlerMixIn`. Contains path resolution logic in
        `field_class` & `field` properties.

        Usage:
            # import path to exact class
           field = LazyField('path.to.SomeClass')

           # name of `LazyFieldHandlerMixIn` subclass
           field = LazyField('LazyFieldHandlerMixInSubclass')

        >>> LazyField('rest_framework.fields.Field').field_class
        <class 'rest_framework.fields.Field'>

        >>> class NamedSerializer(LazyFieldHandlerMixIn, ModelSerializer): pass
        >>> LazyField('NamedSerializer').field_class
        <class 'pik.api.lazy_field.NamedSerializer'>

        >>> LazyField('UnknownNamedSerializer').field_class
        Traceback (most recent call last):
            ...
        pik.api.lazy_field.LazySerializerNotFound: UnknownNamedSerializer

     """

    source = None

    def update(self, instance, validated_data):
        raise NotImplementedError()

    def create(self, validated_data):
        raise NotImplementedError()

    def __init__(self, path, ref_name=None, *args, **kwargs):  # noqa: super-init-not-called
        self.path = path
        self.args = args
        self.kwargs = kwargs
        self._process_ref_name(ref_name)

    @cached_property
    def field_class(self):
        if '.' in self.path:
            return import_string(self.path)
        if self.path not in ModelSerializerRegistratorMetaclass.SERIALIZERS:
            raise LazySerializerNotFound(self.path)
        return ModelSerializerRegistratorMetaclass.SERIALIZERS[self.path]

    @property
    def field(self):
        return self.field_class(*self.args, **self.kwargs)

    def to_internal_value(self, data):
        pass

    def to_representation(self, value):
        pass

    def _process_ref_name(self, ref_name):
        """ Resolve ref_name from source Class path. Needed for DRF Yasg
            serializer resolution mechanism """

        if not ref_name:
            ref_name = self.path.split('.')[-1]
            if ref_name.endswith('Serializer'):
                ref_name = ref_name[:-len('Serializer')]
        self.Meta = type('Meta', (), {'ref_name': ref_name})  # noqa: invalid-name


class ModelSerializerRegistratorMetaclass(SerializerMetaclass):
    """ MetaClass for LazyFieldHandlerMixIn+ModelSerializer subclasses
        registration

        >>> class TestRegistered(LazyFieldHandlerMixIn, ModelSerializer): pass
        >>> ModelSerializerRegistratorMetaclass.SERIALIZERS['TestRegistered']
        <class 'pik.api.lazy_field.TestRegistered'>

        >>> class TestRegistered(LazyFieldHandlerMixIn, ModelSerializer): pass
        Traceback (most recent call last):
            ...
        pik.api.lazy_field.LazySerializerRegistrationConflict: ...

    """
    SERIALIZERS = {}

    def __new__(cls, *args, **kwargs):
        new = super().__new__(cls, *args, **kwargs)
        if issubclass(new, ModelSerializer):
            if new.__name__ in cls.SERIALIZERS:
                raise LazySerializerRegistrationConflict(
                    (new, cls.SERIALIZERS[new.__name__]))
            cls.SERIALIZERS[new.__name__] = new
        return new


class LazyFieldHandlerMixIn(metaclass=ModelSerializerRegistratorMetaclass):
    """ `ModelSerializer` compatible `MixIn` for resolving `LazyField` into
        instance of class located by its' path
        >>> from rest_framework.serializers import Serializer

        >>> class TestSerializer(LazyFieldHandlerMixIn, Serializer):
        ...   field = LazyField('rest_framework.fields.Field')
        >>> TestSerializer().get_fields()['field'].__class__
        <class 'rest_framework.fields.Field'>

        >>> class TestLazyNamed(LazyFieldHandlerMixIn, ModelSerializer): pass
        >>> class TestSerializer(LazyFieldHandlerMixIn, Serializer):
        ...   field = LazyField('TestLazyNamed')
        >>> TestSerializer().get_fields()['field'].__class__
        <class 'pik.api.lazy_field.TestLazyNamed'>

    """

    def get_fields(self, *args, **kwargs):
        parents = []
        parent = getattr(self, 'parent', None)
        while parent:
            parents.append(type(parent))
            parent = parent.parent

        fields = super().get_fields(*args, **kwargs)

        for name, field in list(fields.items()):
            if not isinstance(field, LazyField):
                continue
            is_subclass = (parents and (
                issubclass(field.field_class, tuple(parents))
                or reduce(or_, [isinstance(parent, field.field_class)
                                for parent in parents])))
            if is_subclass:
                if name in fields:
                    del fields[name]
                continue
            serializer = field.field
            fields[name] = serializer
        return fields
