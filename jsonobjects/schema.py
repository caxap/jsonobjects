#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from functools import wraps
from .exceptions import ValidationError
from .fields import Field
from .utils import NULL


__all__ = ['Schema']


class SchemaMetaClass(type):

    @classmethod
    def _get_declared_fields(mcs, bases, attrs):
        fields = []

        for attr_name, obj in list(attrs.items()):
            if isinstance(obj, Field):
                fields.append((attr_name, attrs.pop(attr_name)))

        for base in reversed(bases):
            if hasattr(base, '_declared_fields'):
                fields = list(base._declared_fields.items()) + fields

        return dict(fields)

    def __new__(mcs, name, bases, attrs):
        attrs['_declared_fields'] = mcs._get_declared_fields(bases, attrs)
        return super(SchemaMetaClass, mcs).__new__(mcs, name, bases, attrs)


class Schema(Field):

    __metaclass__ = SchemaMetaClass

    result_factory = NULL

    def __init__(self, source=None, **kwargs):
        result_factory = kwargs.pop('result_factory', NULL)
        self.result_factory = result_factory or self.result_factory
        super(Schema, self).__init__(source=source, **kwargs)

    @property
    def fields(self):
        if not hasattr(self, '_fields'):
            self._fields = {}
            declared_fields = copy.deepcopy(self._declared_fields)
            for name, field in declared_fields.items():
                field.bind(name, self)
                self._fields[name] = field
        return self._fields

    def find(self, data):
        if not self.source:
            return data
        return super(Schema, self).find(data)

    def convert_to_type(self, value):
        result = {}
        errors = []
        for _, field in self.fields.items():
            validate_method = getattr(self, 'validate_' + field.field_name, None)
            raw_value = field.find(value)
            try:
                validated_value = field.run_validation(raw_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as e:
                errors.append(ValidationError(e.messages, field.field_name))
            else:
                result[field.field_name] = validated_value

        if errors:
            raise ValidationError(errors, self.field_name)

        if self.result_factory is not NULL:
            result = self.result_factory(result)

        return result

    def as_decorator(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.parse(func(*args, **kwargs))
        return wrapper
