from structure import Run, Element
import unittest

class RunTests(unittest.TestCase):

    def test_wrapping_with_words_as_runs(self):
        r =  Run()
        for s in 'this| is |a |piece| of| text |that| is |somewhat| long'.split('|'):
            r.append(Element.from_text(s, None))

        self.assertEqual('this is a piece of text that is somewhat long', r.as_str(1000))
        self.assertEqual('this is a piece of\ntext that is\nsomewhat long', r.as_str(20))
        self.assertEqual('this is a piece of text\nthat is somewhat long', r.as_str(25))

    def test_wrapping_with_long_runs(self):
        r =  Run()
        r.append(Element.from_text('one two ', None))
        r.append(Element.from_text('bright gloomy', 'strong'))
        r.append(Element.from_text(' three four five', None))

        self.assertEqual('one two **bright gloomy** three four five', r.as_str(10000))
        self.assertEqual('one\ntwo\n**bright\ngloomy**\nthree\nfour\nfive', r.as_str(0))
        self.assertEqual('one two\n**bright\ngloomy**\nthree four\nfive', r.as_str(10))

    def test_wrapping_with_indent(self):
        r =  Run()
        r.append(Element.from_text('one two ', None))
        r.append(Element.from_text('bright gloomy', 'strong'))
        r.append(Element.from_text(' three four five', None))

        self.assertEqual('one two **bright gloomy** three four five', r.as_str(10000, 2))
        self.assertEqual('one\n  two\n  **bright\n  gloomy**\n  three\n  four\n  five', r.as_str(0, 2))
        self.assertEqual('one two\n  **bright\n  gloomy**\n  three\n  four\n  five', r.as_str(10, 2))
