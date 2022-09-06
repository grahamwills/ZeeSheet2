from unittest import TestCase

from common import Spacing
from structure.style import Style, Defaults


class TestStyle(TestCase):

    def test_default(self):
        # Tests a few items
        self.assertEqual(Defaults.base.name, 'default')
        self.assertEqual(Defaults.base.parent, None)
        self.assertEqual(Defaults.base.text.align, 'left')
        self.assertEqual(Defaults.base.font.family, 'Helvetica')
        self.assertEqual(Defaults.base.box.opacity, 0.0)
        self.assertEqual(Defaults.base.box.padding, Spacing(0, 0, 0, 0))

    def test_initialization(self):
        s = Style('allowed_name')
        self.assertIsNotNone(s.font)
        self.assertIsNotNone(s.text)
        self.assertIsNotNone(s.box)
        self.assertRaises(ValueError, lambda: Style('bad name'))
        self.assertRaises(ValueError, lambda: Style('1badname'))

    def test_to_definition_default(self):
        self.assertEqual('text-color:black; text-opacity:1.0; text-align:left; text-indent:0; '
                         'font-family:Helvetica; font-size:12; font-style:normal; '
                         'border:none; border-width:1; '
                         'border-color:black; border-opacity:1.0; '
                         'background-color:white; background-opacity:0.0; '
                         'margin:0; indent:0', Defaults.base.to_definition())

    def test_to_definition_empty(self):
        self.assertEqual('inherit:default', Style('test', 'default').to_definition())
