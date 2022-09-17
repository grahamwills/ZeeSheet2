import unittest

from structure import Run, Element


class RunTests(unittest.TestCase):

    def test_wrapping_with_words_as_runs(self):
        r = Run()
        for s in 'this| is |a |piece| of| text |that| is |somewhat| long'.split('|'):
            r.append(Element(s))

        self.assertEqual('this is a piece of text that is somewhat long', r.to_rst(1000))
        self.assertEqual('this is a piece of\ntext that is\nsomewhat long', r.to_rst(20))
        self.assertEqual('this is a piece of text\nthat is somewhat long', r.to_rst(25))

    def test_wrapping_with_long_runs(self):
        r = Run()
        r.append(Element('one two '))
        r.append(Element('bright gloomy', 'strong'))
        r.append(Element(' three four five'))

        self.assertEqual('one two **bright gloomy** three four five', r.to_rst(10000))
        self.assertEqual('one\ntwo\n**bright\ngloomy**\nthree\nfour\nfive', r.to_rst(0))
        self.assertEqual('one two\n**bright\ngloomy**\nthree four\nfive', r.to_rst(10))

    def test_wrapping_with_indent(self):
        r = Run()
        r.append(Element('one two '))
        r.append(Element('bright gloomy', 'strong'))
        r.append(Element(' three four five'))

        self.assertEqual('one two **bright gloomy** three four five', r.to_rst(10000, 2))
        self.assertEqual('one\n  two\n  **bright\n  gloomy**\n  three\n  four\n  five', r.to_rst(0, 2))
        self.assertEqual('one two\n  **bright\n  gloomy**\n  three\n  four\n  five', r.to_rst(10, 2))
