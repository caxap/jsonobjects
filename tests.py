#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import copy
import decimal
import datetime
import unittest
from mock import MagicMock

import jsonobjects as jo
from jsonobjects.fields import get_error_messages


TEST_INPUT = {
    'id': '123',
    'details': {
        'name': 'Test Item',
        'sku': ['001-001', '002-002'],
        'price': 0.99,
        'special': False,
        'tags': ['data', 'test', 'item'],
    },
    'reviews': {
        'top': [
            {'user': 1, 'text': 'Good test item!'},
            {'user': 2, 'text': 'Bad test item!'},
        ],
    },
}


class ReviewSchema(jo.Schema):
    user_id = jo.IntegerField('user', min_value=1)
    first6 = jo.StringField('text', trim_whitespace=True,
                            post_process=lambda s: s[:6])
    verified = jo.BooleanField(required=False, default=False)


class DetailsSchema(jo.Schema):
    name = jo.StringField()
    sku = jo.RegexField('sku[0]', regex=r'[0-9\-]+', dialect='jmespath')
    price = jo.FloatField(min_value=0)
    special = jo.BooleanField(required=False, default=False)
    first_tag = jo.StringField('tags[*] | [0]', dialect='jmespath')
    description = jo.StringField(required=False, default='')


class ItemSchema(jo.Schema):
    id = jo.IntegerField()
    data = DetailsSchema('details')
    reviews = jo.ListField('reviews.top', child=ReviewSchema())


class JsonObjectsTestCase(unittest.TestCase):

    def test_default_path(self):
        data = {'x': {'y': [1, 2], '1': [3, 4], '?': 'any'}}
        self.assertEqual(jo.Path('x.y.1').find(data), 2)
        self.assertEqual(jo.Path('x."1".0').find(data), 3)
        self.assertEqual(jo.Path('x."?"').find(data), 'any')
        self.assertEqual(jo.Path('?.y.0').find(data), 1)
        self.assertRaises(jo.NotFound, jo.Path('x.z').find, data)
        self.assertRaises(jo.NotFound, jo.Path('x.y.z').find, data)
        self.assertRaises(jo.NotFound, jo.Path('x').find, {'x': None})
        self.assertEqual(jo.Path('x', allow_null=True).find({'x': None}), None)

    def test_dialects(self):
        find = jo.path.find
        data = {'x': {'y': 1, 'z': [3, 4]}}
        self.assertEqual(find('x.y', data), 1)
        self.assertEqual(find('x.y', data, 'default'), 1)
        self.assertEqual(find('x.y', data, 'jmespath'), 1)
        self.assertRaises(jo.GenericError, find, 'x.y', data, 'dummy')

    def test_limit_validators(self):
        limit = 5
        max_value = jo.MaxValue(limit)
        min_value = jo.MinValue(limit)
        max_length = jo.MaxLength(limit)
        min_length = jo.MinLength(limit)

        max_value(1)
        min_value(10)
        max_length('1')
        min_length('1' * 10)

        self.assertRaises(jo.ValidationError, max_value, 10)
        self.assertRaises(jo.ValidationError, min_value, 1)
        self.assertRaises(jo.ValidationError, max_length, '1' * 10)
        self.assertRaises(jo.ValidationError, min_length, '1')

        for v in [max_value, min_value, max_length, min_length]:
            self.assertEqual(v.params.get('limit'), limit)

    def test_regex_validators(self):
        regex = r'^(\+|\-)?[1-9][0-9\.]*$'
        match = jo.RegexValidator(regex, flags=re.I)
        not_match = jo.RegexValidator(regex, inverse_match=True, flags=re.I)

        match('-1.0')
        not_match('abc')

        self.assertRaises(jo.ValidationError, match, 'abc')
        self.assertRaises(jo.ValidationError, not_match, '-1.0')

    def test_choices_validators(self):
        choices = (1, 2, 3)
        only123 = jo.ChoiceValidator(choices)
        only123(1)
        self.assertRaises(jo.ValidationError, only123, 0)

        choices = ((1, 'One'), (2, 'Two'), (3, 'Three'))
        only123 = jo.ChoiceValidator(choices)
        only123(1)
        self.assertRaises(jo.ValidationError, only123, 0)

    def test_base_field(self):
        f = jo.Field()
        self.assertTrue(f.required)
        self.assertIs(f.default, jo.NULL)
        self.assertFalse(f.null)
        self.assertFalse(f.blank)
        self.assertEqual(f.validators, [])
        self.assertEqual(f.post_process, [])
        self.assertIsNone(f.dialect)
        self.assertIsNone(f.parent)
        self.assertIsNone(f.field_name)
        self.assertIsNone(f.source)
        self.assertEqual(f.error_messages, get_error_messages(f),
                         jo.Field.default_error_messages)

        # Deepcopy support
        self.assertIsNotNone(f._args)
        self.assertIsNotNone(f._kwargs)
        self.assertIsNot(copy.deepcopy(f), f)

        # Binding
        f.bind('test', jo.Field())
        self.assertEqual(f.source, 'test')
        self.assertEqual(f.field_name, 'test')
        self.assertIsNotNone(f.parent)

        # Helpers
        self.assertRaises(AssertionError, jo.Field, required=False)
        self.assertRaises(jo.ValidationError, f.fail, 'null')
        self.assertRaises(AssertionError, f.fail, 'no_such_error')

        # Alternative keys
        data = {'x': {'y': 1}}
        f = jo.Field(['x.z', 'x.y'])
        self.assertEqual(f.parse(data), f(data), 1)

        # Custom validation & processing
        validate = MagicMock()
        post_process = MagicMock()
        f = jo.Field('x.y', validators=[validate], post_process=[post_process])
        f(data)
        validate.assert_called_once_with(1)
        post_process.assert_called_once_with(1)

    def test_field_empty_values_validation(self):
        # required, not empty, not null
        f = jo.Field('x.y')
        self.assertRaises(jo.ValidationError, f, {'x': 1})
        self.assertRaises(jo.ValidationError, f, {'x': None})
        self.assertRaises(jo.ValidationError, f, {'x': {'y': None}})

        # not required (may be `None`), not empty
        f = jo.Field('x.y', required=False, default=object())
        self.assertEqual(f({'x': 1}), f.default)
        self.assertEqual(f({'x': None}), f.default)
        self.assertEqual(f({'x': {'y': None}}), f.default)
        self.assertEqual(f({'x': {'y': 1}}), 1)
        self.assertRaises(jo.ValidationError, f, {'x': {'y': []}})
        self.assertRaises(jo.ValidationError, f, {'x': {'y': ''}})

        # required, may be empty
        f = jo.Field('x.y', default=object(), blank=True)
        self.assertRaises(jo.ValidationError, f, {'x': 1})
        self.assertRaises(jo.ValidationError, f, {'x': None})
        self.assertRaises(jo.ValidationError, f, {'x': {'y': None}})
        self.assertEqual(f({'x': {'y': 1}}), 1)
        self.assertEqual(f({'x': {'y': []}}), [])
        self.assertEqual(f({'x': {'y': ''}}), '')

    def test_bool_field(self):
        f = jo.BooleanField('x')

        for v in [1, '1', 'true', 't', 'y', 'yes', True, [1], {'y': 1}]:
            self.assertTrue(f({'x': v}))

        for v in [0, '0', 'false', 'f', 'n', 'no', False, [], {}]:
            self.assertFalse(f({'x': v}))

        f = jo.BooleanField('x', required=False, default=None, null=True)
        self.assertIsNone(f({'x': None}))

    def test_string_field(self):
        f = jo.StringField('x')
        self.assertEqual(f({'x': 1}), '1')
        self.assertEqual(f({'x': u'й'}), u'й')
        self.assertEqual(f({'x': u'й'.encode('utf-8')}), u'й')
        self.assertRaises(jo.ValidationError, f, {'x': ''})

        f = jo.StringField('x', min_length=5, max_length=10, trim_whitespace=True)
        self.assertEqual(f({'x': '     123456     '}), '123456')
        self.assertRaises(jo.ValidationError, f, {'x': '1'})
        self.assertRaises(jo.ValidationError, f, {'x': '1' * 11})

    def test_integer_field(self):
        f = jo.IntegerField('x')
        self.assertEqual(f({'x': 1}), 1)
        self.assertEqual(f({'x': 1.0}), 1)
        self.assertEqual(f({'x': '1'}), 1)
        self.assertEqual(f({'x': '1.00'}), 1)
        self.assertRaises(jo.ValidationError, f, {'x': 'x'})

        f = jo.IntegerField('x', min_value=5, max_value=10)
        self.assertEqual(f({'x': 5}), 5)
        self.assertEqual(f({'x': 7}), 7)
        self.assertEqual(f({'x': 10}), 10)

    def test_float_field(self):
        f = jo.IntegerField('x')
        self.assertEqual(f({'x': 1}), 1.)
        self.assertEqual(f({'x': 1.}), 1.)
        self.assertEqual(f({'x': '1'}), 1.)
        self.assertEqual(f({'x': '1.00'}), 1.)
        self.assertRaises(jo.ValidationError, f, {'x': 'x'})

        f = jo.IntegerField('x', min_value=5, max_value=10)
        self.assertEqual(f({'x': 5}), 5.)
        self.assertEqual(f({'x': 7}), 7.)
        self.assertEqual(f({'x': 10}), 10.)

    def test_decimal_field(self):
        f = jo.DecimalField('x', min_value=decimal.Decimal('5'))
        self.assertEqual(f({'x': '5.001'}), decimal.Decimal('5.001'))
        self.assertRaises(jo.ValidationError, f, {'x': 'NaN'})
        self.assertRaises(jo.ValidationError, f, {'x': 'Inf'})
        self.assertRaises(jo.ValidationError, f, {'x': 'abc'})

    def test_date_field(self):
        now = datetime.datetime.utcnow()
        f = jo.DateField('x')
        self.assertEqual(f({'x': now.date()}), now.date())
        self.assertEqual(f({'x': '2015-03-13'}),
                         f({'x': '2015-03-13 12:00:00'}),
                         datetime.datetime(2015, 3, 13).date())
        self.assertRaises(jo.ValidationError, f, {'x': now})
        self.assertRaises(jo.ValidationError, f, {'x': 1})

        f = jo.DateField('x', formats=['%Y-%m-%d'])
        self.assertEqual(f({'x': '2015-03-13'}),
                         datetime.datetime(2015, 3, 13).date())

    def test_datetime_field(self):
        now = datetime.datetime.utcnow()
        f = jo.DateTimeField('x')
        self.assertEqual(f({'x': now}), now)
        self.assertEqual(f({'x': '2015-03-13'}),
                         datetime.datetime(2015, 3, 13))
        self.assertEqual(f({'x': '2015-03-13 12:00:00'}),
                         datetime.datetime(2015, 3, 13, 12))
        self.assertRaises(jo.ValidationError, f, {'x': now.date()})
        self.assertRaises(jo.ValidationError, f, {'x': 1})

        f = jo.DateTimeField('x', formats=['%Y-%m-%d'])
        self.assertEqual(f({'x': '2015-03-13'}),
                         datetime.datetime(2015, 3, 13))

    def test_regex_field(self):
        f = jo.RegexField('x', r'^[0-9]+$', flags=re.I)
        self.assertEqual(f({'x': '123'}), '123')
        self.assertRaises(jo.ValidationError, f, {'x': 'abc'})

        f = jo.RegexField('x', r'^[0-9]+$', flags=re.I, inverse_match=True)
        self.assertEqual(f({'x': 'abc'}), 'abc')
        self.assertRaises(jo.ValidationError, f, {'x': '123'})

    def test_list_field(self):
        f = jo.ListField('x')
        self.assertEqual(set(f({'x': {1, None, 'abc'}})), set([1, None, 'abc']))
        self.assertRaises(jo.ValidationError, f, {'x': 1})

        f = jo.ListField('x', child=jo.IntegerField())
        self.assertEqual(f({'x': [1, '2', 3.0]}), [1, 2, 3])
        self.assertRaises(jo.ValidationError, f, {'x': ['abc']})
        self.assertRaises(jo.ValidationError, f, {'x': [None]})

        f = jo.ListField('x', child=jo.IntegerField(null=True))
        self.assertEqual(f({'x': [1, None]}), [1, None])

        f = jo.ListField('x', child=jo.ListField())
        self.assertEqual(f({'x': [[1], [2]]}), [[1], [2]])

        f = jo.ListField('x', child=jo.IntegerField(min_value=5))
        self.assertRaises(jo.ValidationError, f, {'x': [1, 5]})

    def test_dict_field(self):
        f = jo.DictField('x')
        self.assertEqual(f({'x': {'y': {}, 'z': None}}), {'y': {}, 'z': None})

        f = jo.DictField('x', child=jo.IntegerField())
        self.assertEqual(f({'x': {'y': '1.0', 'z': 2.}}), {'y': 1, 'z': 2})

        f = jo.DictField('x', child=jo.IntegerField(null=True))
        self.assertEqual(f({'x': {'y': 1, 'z': None}}), {'y': 1, 'z': None})

        f = jo.DictField('x', child=jo.IntegerField(min_value=5))
        self.assertRaises(jo.ValidationError, f, {'x': {'y': 1}})

    def test_schema(self):
        s = DetailsSchema('details')
        data_ret = {
            'sku': '001-001',
            'first_tag': 'data',
            'name': u'Test Item',
            'price': 0.99,
            'special': False,
            'description': ''
        }
        self.assertEqual(s(TEST_INPUT), data_ret)

        s = ReviewSchema('reviews.top[0]', dialect='jmespath')
        reviews_ret = [{
            'verified': False,
            'first6': u'Good t',
            'user_id': 1,
        }, {
            'verified': False,
            'first6': u'Bad te',
            'user_id': 2,
        }]
        self.assertEqual(s(TEST_INPUT), reviews_ret[0])

        s = ItemSchema()
        item_ret = {
            'id': 123,
            'data': data_ret,
            'reviews': reviews_ret,
        }
        self.assertEqual(s(TEST_INPUT), item_ret)

    def test_schema_inheritance(self):

        class Foo(jo.Schema):
            x = jo.IntegerField()

        class Bar(Foo):
            x = jo.IntegerField(post_process=lambda x: 2 * x)

        f1 = Foo()
        f2 = Bar()

        data = {'x': 1}
        self.assertEqual(f1(data)['x'], 1)
        self.assertEqual(f2(data)['x'], 2)

    def test_nested_validation_errors(self):
        class Foo(jo.Schema):
            foo = jo.IntegerField()

        class Bar(jo.Schema):
            bar = Foo()

        try:
            Bar()({'bar': {'foo': None}})
            self.assertFalse(True)
        except jo.ValidationError as e:
            self.assertEqual(e.flatten_messages, [{
                'bar': [
                    {'foo': ['This field is required.']}
                ]}
            ])


if __name__ == '__main__':
    unittest.main()
