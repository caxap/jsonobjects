#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from collections import OrderedDict
from .exceptions import ValidationError
from .utils import basestring_type

__all__ = ['MinValue', 'MaxValue', 'MinLength', 'MaxLength', 'RegexValidator',
           'ChoiceValidator']


class BaseValidator(object):
    message = 'This value is invalid.'
    predicate = lambda self, v: True

    def __init__(self, message=None, params=None, field_name=None):
        self.message = message or self.message
        self.field_name = field_name
        self.params = params or {}

    def validate(self, value):
        if not self.predicate(value):
            params = dict(self.params or {}, value=value)
            message = self.message.format(**params)
            raise ValidationError(message, self.field_name)
        return value

    def __call__(self, value):
        return self.validate(value)


class MinValue(BaseValidator):
    predicate = lambda self, v: v >= self.limit
    message = 'Ensure this value is greater than or equal to {limit}'

    def __init__(self, limit, **kwargs):
        kwargs.setdefault('params', {}).setdefault('limit', limit)
        super(MinValue, self).__init__(**kwargs)
        self.limit = limit


class MaxValue(BaseValidator):
    predicate = lambda self, v: v <= self.limit
    message = 'Ensure this value is less than or equal to {limit}.'

    def __init__(self, limit, **kwargs):
        kwargs.setdefault('params', {}).setdefault('limit', limit)
        super(MaxValue, self).__init__(**kwargs)
        self.limit = limit


class MinLength(BaseValidator):
    predicate = lambda self, v: len(v) >= self.limit
    message = 'Ensure this value has at least {limit} characters.'

    def __init__(self, limit, **kwargs):
        kwargs.setdefault('params', {}).setdefault('limit', limit)
        super(MinLength, self).__init__(**kwargs)
        self.limit = limit


class MaxLength(BaseValidator):
    predicate = lambda self, v: len(v) <= self.limit
    message = 'Ensure this value has no more than {limit} characters.'

    def __init__(self, limit, **kwargs):
        kwargs.setdefault('params', {}).setdefault('limit', limit)
        super(MaxLength, self).__init__(**kwargs)
        self.limit = limit


class RegexValidator(BaseValidator):
    message = 'This value does not match the required pattern.'
    regex = ''
    inverse_match = False
    flags = 0

    def __init__(self, regex=None, inverse_match=None, flags=None, **kwargs):
        if regex is not None:
            self.regex = regex
        if inverse_match is not None:
            self.inverse_match = inverse_match
        if flags is not None:
            self.flags = flags

        if self.flags and not isinstance(self.regex, basestring_type):
            raise TypeError("If the flags are set, regex must be a regular expression string.")

        self.regex = re.compile(self.regex, self.flags)

        super(RegexValidator, self).__init__(**kwargs)

    def predicate(self, value):
        ret = bool(self.regex.search(value))
        return not ret if self.inverse_match else ret


def _to_choices_dict(choices):
    ret = OrderedDict()
    for choice in choices:
        if isinstance(choice, (list, tuple)):
            # paired choice (key, display value)
            key, value = choice
            ret[key] = value
        else:
            # single choice
            ret[choice] = choice
    return ret


class ChoiceValidator(BaseValidator):
    message = 'This value is not a valid choice.'

    def __init__(self, choices, **kwargs):
        self.choices = _to_choices_dict(choices)
        super(ChoiceValidator, self).__init__(**kwargs)

    def predicate(self, value):
        return value in self.choices
