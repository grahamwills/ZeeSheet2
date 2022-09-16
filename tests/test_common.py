from unittest import TestCase

from common import parse


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
