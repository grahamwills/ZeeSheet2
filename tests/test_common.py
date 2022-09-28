import math
import re
from unittest import TestCase

from common import parse, to_str, name_of, Rect


class WithNameField:
    def __init__(self, name):
        self.name = name


class WithNameMethod:
    def name(self):
        return 'name_from_method'


class TestCommon(TestCase):

    def test_parse_nothing(self):
        self.assertEqual([], parse(''))
        self.assertEqual([], parse('    '))
        self.assertEqual([], parse('  \t\n  '))

    def test_parse_single(self):
        self.assertEqual([('a', 'b')], parse('a:b'))
        self.assertEqual([('a', 'b')], parse('a:    b'))
        self.assertEqual([('a', 'b')], parse('\ta:    b\n'))
        self.assertEqual([('a', 'b')], parse('a=b'))
        self.assertEqual([('a', 'b')], parse('a=    b'))
        self.assertEqual([('a', 'b')], parse('\ta=    b\n'))

    def test_parse_two(self):
        self.assertEqual([('a', 'b'), ('c', 'd')], parse('a:b c= d'))

    def test_parse_no_equals(self):
        self.assertEqual([('x', ''), ('a', 'b'), ('c', ''), ('d', '')], parse('x a:b c d'))

    def test_quotes(self):
        self.assertEqual([('a', 'bb cc'), ('d', 'ee f g')], parse("a='bb cc' d:'ee f g'"))
        self.assertEqual([('a', 'bb cc'), ('d', 'ee f g')], parse('a="bb cc" d:"ee f g"'))

    def test_to_str_for_numerics(self):
        self.assertEqual('34', to_str(34))
        self.assertEqual('34', to_str(34.0))
        self.assertEqual('34', to_str(34.0001))
        self.assertEqual('-34.001', to_str(-34.001))
        self.assertEqual('34.001', to_str(34.0007))

        self.assertEqual('34.0001', to_str(34.0001, places=4))
        self.assertEqual('34.1', to_str(34.1234, places=1))
        self.assertEqual('35', to_str(34.91234, places=0))
        self.assertEqual('-12M', to_str(-12345678, places=0))
        self.assertEqual('12.346M', to_str(12345678))
        self.assertEqual('12M', to_str(12000078))

    def test_to_str_for_non_numerics(self):
        self.assertEqual('hello', to_str('hello'))
        self.assertEqual('(5, 7)', to_str((5, 7)))
        self.assertEqual('\u221e', to_str(math.inf))
        self.assertEqual('-\u221e', to_str(-math.inf))
        self.assertEqual('nan', to_str(math.nan))
        self.assertEqual('None', to_str(None))

    def test_name_of_with_standard_types(self):
        self.assertEqual('hello', name_of('hello'))
        self.assertEqual('(5, 7)', name_of((5, 7)))
        self.assertEqual('(5, 7)', name_of((5, 7)))
        self.assertEqual('(5, 6, 7, 8, …)', name_of((5, 6, 7, 8, 9, 10, 11)))
        self.assertEqual('(5, 6, 7, 8, …)', name_of([5, 6, 7, 8, 9, 10, 11]))
        self.assertEqual('-\u221e', name_of(-math.inf))
        self.assertEqual('nan', name_of(math.nan))
        self.assertEqual('None', name_of(None))

    def test_name_of_classes(self):
        self.assertEqual('fred', name_of(WithNameField('fred')))
        self.assertEqual('(fred, wilma)', name_of((WithNameField('fred'), WithNameField('wilma'))))
        self.assertEqual('this is a ve…g name indeed', name_of(WithNameField('this is a very long name indeed')))
        self.assertEqual('name_from_method', name_of(WithNameMethod()))
        self.assertIsNotNone(re.match('Rect\\(....\\)', name_of(Rect(1, 2, 3, 4))),
                             'Wrong format: ' + name_of(Rect(1, 2, 3, 4)))
        self.assertIsNotNone(re.match('ConnectionError\\(....\\)', name_of(ConnectionError())),
                             'Wrong format: ' + name_of(ConnectionError()))
