# -*- coding: utf-8 -*-


__all__ = ['GenericError', 'NotFound', 'ValidationError']

from .utils import to_iterable, basestring_type


class GenericError(Exception):
    pass


class NotFound(GenericError):

    def __init__(self, source):
        GenericError.__init__(self)
        self.source = source

    def __str__(self):
        return self.source

    def __repr__(self):
        cls_name = self.__class__.__name__
        return '{cls_name}({source!r},)'.format(cls_name=cls_name,
                                                source=self.source)


class ValidationError(GenericError):

    def __init__(self, messages, field_name=None):
        GenericError.__init__(self)
        self.messages = to_iterable(messages)
        self.field_name = field_name

    @property
    def flatten_messages(self):
        def walk(e):
            if isinstance(e, basestring_type):
                return e
            return {e.field_name: [walk(m) for m in e.messages]}

        messages = walk(self)
        # Unwrap top level exception for `Schema`
        if self.field_name is None:
            messages = messages[self.field_name]
        return messages

    def __repr__(self):
        cls_name = self.__class__.__name__
        msg = '{cls_name}({field_name!r}, {messages})'
        return msg.format(cls_name=cls_name,
                          field_name=self.field_name,
                          messages=self.messages)

    def __str__(self):
        return str(self.messages)
