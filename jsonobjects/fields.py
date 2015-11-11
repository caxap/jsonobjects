#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import copy
import inspect
import decimal
import datetime
from collections import Mapping
from . import path
from .exceptions import NotFound, ValidationError
from .validators import (
    MinValue, MaxValue, MaxLength, MinLength, RegexValidator
)
from .utils import (
    NULL, ISO_8601, smart_bool, to_iterable, is_non_str_iterable, to_unicode,
    basestring_type, unicode_type
)

try:
    from dateutil.parser import parse as parse_datetime
except ImportError:
    parse_datetime = None


__all__ = ['Field', 'BooleanField', 'StringField', 'IntegerField',
           'FloatField', 'DecimalField', 'DateField', 'DateTimeField',
           'RegexField', 'ListField', 'DictField']


def get_error_messages(instance):
    messages = {}
    for cls in reversed(instance.__class__.__mro__):
        messages.update(getattr(cls, 'default_error_messages', {}))
    return messages


class Field(object):
    default_blank_value = NULL
    default_error_messages = {
        'required': 'This field is required.',
        'null': 'This field may not be null.',
        'blank': 'This field may not be empty.',
    }

    def __init__(self, source=None, default=NULL, required=True, null=False,
                 blank=False, validators=None, post_process=None, dialect=None):
        assert required or default is not NULL, '`default` should be set for not required field.'

        self.source = source
        self.default = default
        self.required = required
        self.null = null
        self.blank = blank
        self.validators = to_iterable(validators) if validators else []
        self.post_process = to_iterable(post_process) if post_process else []
        self.dialect = dialect
        self.error_messages = get_error_messages(self)

        if self.default_blank_value is not NULL:
            if default is not NULL:
                self.default_blank_value = default

        self.parent = None
        self.field_name = None

    def bind(self, field_name, parent):
        self.parent = parent
        self.field_name = field_name
        if self.source is None:
            self.source = field_name

    def is_null(self, value):
        return value is None

    def is_blank(self, value):
        try:
            return len(value) == 0
        except (TypeError, ValueError):
            pass
        return False

    def find(self, data):
        if not self.source:
            cls_name = self.__class__.__name__
            input_type = type(data).__name__
            name = self.field_name or '<unbound>'
            msg = (
                "`{cls_name}.source` attribute is required to find `{name}` "
                "field from {input_type}."
            ).format(cls_name=cls_name, name=name, input_type=input_type)
            raise AssertionError(msg)

        # Allow to search for multiple sources
        for src in to_iterable(self.source):
            try:
                return path.find(src, data, self.dialect)
            except NotFound:
                pass
        return NULL

    def validate_empty_values(self, value):
        if value is NULL:
            if self.required:
                self.fail('required')
            value = self.default() if callable(self.default) else self.default
            return True, value

        # Only for case when `dialect` supports `None` result
        if self.is_null(value):
            if not self.null:
                self.fail('null')
            return True, None

        if self.is_blank(value):
            if not self.blank:
                self.fail('blank')

            blank = self.default_blank_value
            if blank is not NULL:
                value = blank() if callable(blank) else blank
            return True, value

        return False, value

    def run_validators(self, value):
        if self.validators:
            for validate in self.validators:
                validate(value)
        return value

    def validate(self, value):
        return value

    def run_validation(self, value):
        is_empty, value = self.validate_empty_values(value)
        if is_empty:
            return value
        value = self.convert_to_type(value)
        self.run_validators(value)
        value = self.validate(value)
        value = self.run_post_process(value)
        return value

    def run_post_process(self, value):
        if self.post_process:
            for process in self.post_process:
                value = process(value)
        return value

    def convert_to_type(self, value):
        return value

    def fail(self, key, **kwargs):
        try:
            msg = self.error_messages[key]
        except KeyError:
            cls_name = self.__class__.__name__
            msg = (
                "ValidationError raised by `{cls_name}`, but error key "
                "`{key}` does not exist in the `error_messages` dictionary."
            ).format(cls_name=cls_name, key=key)
            raise AssertionError(msg)

        raise ValidationError(msg.format(**kwargs), self.field_name)

    def parse(self, data):
        value = self.find(data)
        return self.run_validation(value)

    def __call__(self, data):
        return self.parse(data)

    def __new__(cls, *args, **kwargs):
        instance = super(Field, cls).__new__(cls)
        instance._args = args
        instance._kwargs = kwargs
        return instance

    def __deepcopy__(self, memo):
        args = copy.deepcopy(self._args)
        kwargs = copy.deepcopy(self._kwargs)
        return self.__class__(*args, **kwargs)


class BooleanField(Field):

    def is_blank(self, value):
        return False

    def convert_to_type(self, value):
        if self.null and value is None:
            return value
        return smart_bool(value)


class StringField(Field):
    default_blank_value = str
    default_error_messages = {
        'invalid': 'A valid string is required.',
        'max_length': 'Ensure this field has no more than {limit} characters.',
        'min_length': 'Ensure this field has at least {limit} characters.'
    }

    def __init__(self, source=None, **kwargs):
        self.trim_whitespace = kwargs.pop('trim_whitespace', True)
        self.encoding = kwargs.pop('encoding', 'utf-8')
        self.errors = kwargs.pop('errors', 'strict')
        self.max_length = kwargs.pop('max_length', None)
        self.min_length = kwargs.pop('min_length', None)

        super(StringField, self).__init__(source, **kwargs)

        if self.max_length is not None:
            message = self.error_messages['max_length']
            self.validators.append(MaxLength(self.max_length, message=message))
        if self.min_length is not None:
            message = self.error_messages['min_length']
            self.validators.append(MinLength(self.min_length, message=message))

    def is_blank(self, value):
        if self.trim_whitespace and hasattr(value, 'strip'):
            value = value.strip()
        return super(StringField, self).is_blank(value)

    def convert_to_type(self, value):
        try:
            if not isinstance(value, basestring_type):
                value = str(value)
            if self.encoding:
                value = to_unicode(value, self.encoding, self.errors)
        except (TypeError, ValueError):
            self.fail('invalid')

        if value and self.trim_whitespace:
            value = value.strip()
        return value


class BaseNumberField(Field):
    default_error_messages = {
        'invalid': 'A valid number is required.',
        'max_value': 'Ensure this field is less than or equal to {limit}.',
        'min_value': 'Ensure this field is greater than or equal to {limit}.',
        'max_string_length': 'String value too large.',
    }
    number_type = NULL

    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, source=None, **kwargs):
        cls_name = self.__class__.__name__
        assert self.number_type is not NULL, (
            '`number_type` property is not defined for `{cls_name}`.'
        ).format(cls_name=cls_name)

        self.max_value = kwargs.pop('max_value', None)
        self.min_value = kwargs.pop('min_value', None)

        super(BaseNumberField, self).__init__(source, **kwargs)

        if self.max_value is not None:
            message = self.error_messages['max_value']
            self.validators.append(MaxValue(self.max_value, message=message))
        if self.min_value is not None:
            message = self.error_messages['min_value']
            self.validators.append(MinValue(self.min_value, message=message))

    def convert_to_type(self, value):
        if isinstance(value, basestring_type):
            value = value.strip()
            if len(value) > self.MAX_STRING_LENGTH:
                self.fail('max_string_length')

        try:
            return self.number_type(value)
        except (ValueError, TypeError):
            self.fail('invalid')


class IntegerField(BaseNumberField):
    default_error_messages = {
        'invalid': 'A valid integer is required.',
    }
    re_decimal = re.compile(r'\.0*\s*$')  # allow e.g. '1.0' as an int, but not '1.2'

    def number_type(self, value):
        return int(self.re_decimal.sub('', str(value)))


class FloatField(BaseNumberField):
    number_type = float

    def __init__(self, source=None, **kwargs):
        self.precision = kwargs.pop('precision', None)
        super(FloatField, self).__init__(source, **kwargs)

    def convert_to_type(self, value):
        value = super(FloatField, self).convert_to_type(value)
        if self.precision:
            value = round(value, self.precision)
        return value


class DecimalField(BaseNumberField):

    def number_type(self, value):
        if not isinstance(value, decimal.Decimal):
            try:
                value = decimal.Decimal(value)
            except decimal.DecimalException:
                self.fail('invalid')

        if value != value:
            self.fail('invalid')

        if value in (decimal.Decimal('Inf'), decimal.Decimal('-Inf')):
            self.fail('invalid')

        return value


class BaseDateField(Field):
    default_error_messages = {
        'invalid': 'A valid date is required. Allowed formats: {formats}.',
        'max_string_length': 'String value too large.',
    }
    default_formats = [ISO_8601]
    MAX_STRING_LENGTH = 1000  # Guard against malicious string inputs.

    def __init__(self, source=None, **kwargs):
        self.formats = kwargs.pop('formats', self.default_formats)
        super(BaseDateField, self).__init__(source, **kwargs)

    def convert_to_type(self, value):
        if isinstance(value, basestring_type):
            value = unicode_type(value.strip())
            if len(value) > self.MAX_STRING_LENGTH:
                self.fail('max_string_length')

            for format in self.formats:
                try:
                    return self.parse_date(value, format)
                except (ValueError, TypeError):
                    continue

        formats_repr = ', '.join([repr(format) for format in self.formats])
        self.fail('invalid', formats=formats_repr)

    def parse_date(self, value, format):
        if format.lower() == ISO_8601:
            assert parse_datetime, (
                '`dateutils` is not installed. Use `pip install dateutils` '
                'command to install this package.'
            )
            return parse_datetime(value)
        else:
            return datetime.datetime.strptime(value, format)


class DateField(BaseDateField):
    default_error_messages = {
        'datetime': 'Expected a date but got a datetime.'
    }

    def convert_to_type(self, value):
        if isinstance(value, datetime.datetime):
            self.fail('datetime')

        if isinstance(value, datetime.date):
            return value

        return super(DateField, self).convert_to_type(value)

    def parse_date(self, value, format):
        return super(DateField, self).parse_date(value, format).date()


class DateTimeField(BaseDateField):
    default_error_messages = {
        'date': 'Expected a datetime but got a date.',
    }

    def convert_to_type(self, value):
        if isinstance(value, datetime.datetime):
            return value

        if isinstance(value, datetime.date):
            self.fail('date')

        return super(DateTimeField, self).convert_to_type(value)


class RegexField(StringField):
    default_error_messages = {
        'invalid': 'This field does not match the required pattern.',
    }

    def __init__(self, source=None, regex=NULL, **kwargs):
        assert regex is not NULL, '`regex` is required paramete.'

        self.flags = kwargs.pop('flags', 0)
        self.inverse_match = kwargs.pop('inverse_match', None)
        super(RegexField, self).__init__(source, **kwargs)
        validator = RegexValidator(regex,
                                   flags=self.flags,
                                   inverse_match=self.inverse_match,
                                   message=self.error_messages['invalid'])
        self.validators.append(validator)


class ListField(Field):
    child = Field(null=True, blank=True)
    default_blank_value = list
    default_error_messages = {
        'invalid_type': "Expected a list of items but got type '{input_type}'.",
        'blank': 'This field may not be empty.',
    }

    def __init__(self, source=None, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        super(ListField, self).__init__(source, **kwargs)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, '`source` attribute is not allowed for `child` field.'

        self.child.bind('', self)

    def convert_to_type(self, value):
        if not is_non_str_iterable(value):
            self.fail('invalid_type', input_type=type(value).__name__)
        return [self.child.run_validation(v) for v in value]


class DictField(Field):
    child = Field(null=True, blank=True)
    default_blank_value = dict
    default_error_messages = {
        'input_type': "Expected a dictionary of items but got type '{input_type}'",
        'blank': 'This field may not be empty.',
    }

    def __init__(self, source=None, **kwargs):
        self.child = kwargs.pop('child', copy.deepcopy(self.child))
        super(DictField, self).__init__(source, **kwargs)

        assert not inspect.isclass(self.child), '`child` has not been instantiated.'
        assert self.child.source is None, '`source` attribute is not allowed for `child` field.'

        self.child.bind('', self)

    def convert_to_type(self, value):
        if not isinstance(value, Mapping):
            self.fail('invalid_type', input_type=type(value).__name__)
        return {to_unicode(k): self.child.run_validation(v)
                for k, v in value.items()}
