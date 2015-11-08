#!/usr/bin/env python
# -*- coding: utf-8 -*-

from collections import Mapping, Sequence
from .exceptions import GenericError, NotFound
from .utils import NULL

try:
    import jmespath
except ImportError:
    jmespath = None


def _unquote(s):
    if s.startswith(('\'', '"')) and s[0] == s[-1]:
        return s[1:-1]
    return s


def _to_index(k):
    try:
        return int(k)
    except (TypeError, ValueError):
        pass


def _is_mapping(v):
    return isinstance(v, Mapping)


def _is_sequence(v):
    return (not _is_mapping(v) and
            (isinstance(v, Sequence) or hasattr(v, '__getitem__')))


class Path(object):
    KEY_TOK, IDX_TOK, ANY_TOK = ('key', 'index', '?')

    def __init__(self, source, delim='.', allow_null=False):
        self.source = source
        self.delim = delim
        self.allow_null = allow_null

    def _head(self, source):
        parts = source.split(self.delim, 1)
        if len(parts) == 1:
            head, tail = parts[0], None
        else:
            head, tail = parts
        return head, tail

    def _token(self, k):
        if k == '?':
            return k, self.ANY_TOK
        elif _to_index(k) is not None:
            return _to_index(k), self.IDX_TOK
        else:
            return _unquote(k), self.KEY_TOK

    def _eval_key(self, k, value):
        return value.get(k, NULL)

    def _eval_index(self, i, value):
        try:
            return value[i]
        except (IndexError, TypeError):
            return NULL

    def _eval_any(self, _, value):
        return value[value.keys()[0]] if value else NULL

    def _eval_attr(self, k, value):
        return getattr(value, k, NULL)

    def _eval(self, key, data):
        k, tok = self._token(key)
        is_map = _is_mapping(data)
        is_idx = _is_sequence(data)

        eval_tok = None
        if is_idx:
            if tok == self.IDX_TOK:
                eval_tok = self._eval_index

        elif is_map:
            if tok == self.ANY_TOK:
                eval_tok = self._eval_any
            elif tok == self.KEY_TOK:
                eval_tok = self._eval_key

        else:
            if tok == self.KEY_TOK:
                eval_tok = self._eval_key

        return eval_tok(k, data) if eval_tok else NULL

    def _walk(self, tail, data):
        head, tail = self._head(tail)
        data = self._eval(head, data)

        if data is NULL:
            raise NotFound(self.source)

        if not tail:
            if not self.allow_null and data is None:
                raise NotFound(self.source)
            return data

        return self._walk(tail, data)

    def find(self, data):
        return self._walk(self.source, data)


def find(source, data, dialect=None):
    if dialect not in DIALECTS:
        allowed = ', '.join([repr(d) for d in DIALECTS if d])
        msg = (
            "Dialect '{dialect}' is not supported; choose one of {allowed}."
        ).format(dialect=dialect, allowed=allowed)
        raise GenericError(msg)
    return DIALECTS[dialect](source, data)


def _best_find(src, data):
    if jmespath:
        return _jmespath_find(src, data)
    else:
        return _defatul_find(src, data)


def _defatul_find(src, data):
    return Path(src).find(data)


def _jmespath_find(src, data):
    assert jmespath, (
        "`jmespath` is not installed. Use `pip install jmespath` command to "
        "install this package."
    )
    value = jmespath.search(src, data)
    # XXX: For `jmespath` it's impossible to detect that value equals to
    # `None` or doesn't exist. So we throw `NotFound` error in both cases.
    # Also `required=` and `null=` field parametes have the same meaning for
    # the `jmespath` dialect.
    if value is None:
        raise NotFound(src)
    return value


DIALECTS = {
    None: _best_find,
    'default': _defatul_find,
    'jmespath': _jmespath_find,
}
