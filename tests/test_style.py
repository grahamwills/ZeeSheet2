from unittest import TestCase

from reportlab.lib.colors import Color

from structure.style import Style, set_style_value, Default


class TestStyle(TestCase):

    def test_default(self):
        s = Default.base
        self.assertEqual(s.text.color, Color(0,0,0))
