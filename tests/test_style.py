from unittest import TestCase

from common import Spacing
from structure.style import Style, Defaults, set_using_definition


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
        self.assertEqual('text-color:black; text-opacity:1; text-align:left; text-indent:0; '
                         'font-family:Helvetica; font-size:12; font-style:normal; '
                         'border:none; border-width:1; '
                         'border-color:black; border-opacity:1; '
                         'background:white; background-opacity:0; '
                         'margin:0; padding:0', Defaults.base.to_definition())

    def test_to_definition_empty(self):
        self.assertEqual('inherit:default', Style('test', 'default').to_definition())

    def test_round_trip_for_default(self):
        base = Defaults.base
        base_def = base.to_definition()
        parsed = Style('default')
        set_using_definition(parsed, base_def)
        parsed_def = parsed.to_definition()
        self.assertEqual(base, parsed)
        self.assertEqual(base_def, parsed_def)

    def test_setting_values(self):
        style = Style('test')
        self.assertEqual('font-family:Arial', style.set('font-family', 'Arial').to_definition())
        self.assertEqual('font-family:Helvetica', style.set('font', 'Helvetica').to_definition())
        self.assertEqual('font-family:Symbol', style.set('font-font', 'Symbol').to_definition())

        style = Style('test')
        self.assertEqual('font-size:1', style.set('font-size', '1.0').to_definition())
        self.assertEqual('font-size:2', style.set('fontSize', '2').to_definition())

        style = Style('test')
        self.assertEqual('text-align:right', style.set('text-align', 'right').to_definition())
        self.assertEqual('text-align:center', style.set('align', 'center').to_definition())
        self.assertEqual('text-align:left', style.set('textAlignment', 'left').to_definition())

        style = Style('test')
        self.assertEqual('text-indent:12', style.set('indent', '12').to_definition())
        self.assertEqual('text-indent:113.39', style.set('textIndent', '4cm').to_definition())

        style = Style('test')
        self.assertEqual('text-color:green', style.set('text-color', 'green').to_definition())
        self.assertEqual('text-color:red', style.set('color', 'red').to_definition())
        self.assertEqual('text-color:purple', style.set('foreground', 'purple').to_definition())
        self.assertEqual('text-color:purple; text-opacity:1', style.set('textOpacity', '1').to_definition())
        self.assertEqual('text-color:purple; text-opacity:0.4', style.set('opacity', '40%').to_definition())

        style = Style('test')
        self.assertEqual('background:green', style.set('box-color', 'green').to_definition())
        self.assertEqual('background:red', style.set('box-background', 'red').to_definition())

        style = Style('test')
        self.assertEqual('background-opacity:0.1', style.set('box-opacity', '0.1').to_definition())
        self.assertEqual('background-opacity:0.8', style.set('box-backgroundOpacity', '80%').to_definition())

        style = Style('test')
        self.assertEqual('border:none', style.set('border', 'none').to_definition())
        self.assertEqual('border:square', style.set('box-border', 'square').to_definition())
        self.assertEqual('border:rounded', style.set('border-method', 'rounded').to_definition())
        self.assertEqual('border:square', style.set('box-style', 'square').to_definition())

        style = Style('test')
        self.assertEqual('border-opacity:1', style.set('border-opacity', '1').to_definition())
        self.assertEqual('border-opacity:0.4', style.set('box-border-opacity', '40%').to_definition())

        style = Style('test')
        self.assertEqual('border-width:1.1', style.set('border-width', '1.1').to_definition())
        self.assertEqual('border-width:1in', style.set('border-line-width', '1in').to_definition())
        self.assertEqual('border-width:10', style.set('box-line-width', '10').to_definition())
        self.assertEqual('border-width:20', style.set('box-border-width', '20').to_definition())
        self.assertEqual('border-width:30', style.set('box-width', '30').to_definition())

        style = Style('test')
        self.assertEqual('padding:2in', style.set('padding', '2in').to_definition())
        self.assertEqual('padding:7 0.5in', style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual('margin:3 2 7 0.5in; padding:7 0.5in', style.set('margin', '3 2 7 0.5in').to_definition())

        style = Style('test')
        self.assertEqual('padding:2in', style.set('padding', '2in').to_definition())
        self.assertEqual('padding:7 0.5in', style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual('padding:3 2 7 0.5in', style.set('box-padding', '3 2 7 0.5in').to_definition())

        style = Style('test')
        self.assertEqual('padding:2in', style.set('padding', '2in').to_definition())
        self.assertEqual('padding:7 0.5in', style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual('padding:3 2 7 0.5in', style.set('box-padding', '3 2 7 0.5in').to_definition())


    def test_bad_settings(self):
        style = Style('test')
        self.assertRaises(AttributeError, lambda: style.set('unknown',  'red'))
        self.assertRaises(ValueError, lambda: style.set('color',  'a strange hue'))
        self.assertRaises(ValueError, lambda: style.set('border',  'squiggly'))
        self.assertRaises(ValueError, lambda: style.set('opacity',  '2'))
        self.assertRaises(ValueError, lambda: style.set('box-opacity',  '-1'))
