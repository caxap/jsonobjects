# -*- coding: utf-8 -*-


__all__ = ['NULL', 'ISO_8601', 'unicode_type', 'basestring_type',
           'utf8', 'to_unicode',
           'is_non_str_iterable', 'to_iterable', 'smart_bool']


NULL = object()
ISO_8601 = 'iso-8601'


if not isinstance(b'', type('')):
    unicode_type = str
    basestring_type = str
else:
    unicode_type = unicode
    basestring_type = basestring


_UTF8_TYPES = (bytes, type(None))


def utf8(value, errors='strict'):
    """Converts a string argument to a byte string.
    If the argument is already a byte string or None, it is returned unchanged.
    Otherwise it must be a unicode string and is encoded as utf8.
    """
    if isinstance(value, _UTF8_TYPES):
        return value
    if not isinstance(value, unicode_type):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value)
        )
    return value.encode('utf-8', errors=errors)


_TO_UNICODE_TYPES = (unicode_type, type(None))


def to_unicode(value, encoding='utf-8', errors='strict'):
    """Converts a string argument to a unicode string.
    If the argument is already a unicode string or None, it is returned
    unchanged.  Otherwise it must be a byte string and is decoded as utf8.
    """
    if isinstance(value, _TO_UNICODE_TYPES):
        return value
    if not isinstance(value, bytes):
        raise TypeError(
            "Expected bytes, unicode, or None; got %r" % type(value)
        )
    return value.decode(encoding, errors=errors)


def is_non_str_iterable(value):
    return (not isinstance(value, basestring_type) and
            hasattr(value, '__iter__'))


def to_iterable(value):
    return value if is_non_str_iterable(value) else [value]


def smart_bool(v):
    try:
        v = v.lower()
        if v in ['true', 't', 'yes', 'y', '1']:
            return True
        if v in ['false', 'f', 'no', 'n', '0']:
            return False
    except AttributeError:
        pass
    return bool(v)
