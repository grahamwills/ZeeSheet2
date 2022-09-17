import warnings
from textwrap import dedent
from unittest import TestCase

from common import Spacing, Rect, Extent
from layout.build import make_complete_styles
from structure import text_to_sheet
from structure.style import Style, Defaults, set_using_definition, BoxStyle


class TestStyle(TestCase):

    def test_default(self):
        # Tests a few items
        self.assertEqual(Defaults.default.name, 'default')
        self.assertEqual(Defaults.default.parent, None)
        self.assertEqual(Defaults.default.text.align, 'left')
        self.assertEqual(Defaults.default.font.family, 'Helvetica')
        self.assertEqual(Defaults.default.box.opacity, 1.0)
        self.assertEqual(Defaults.default.box.padding, Spacing(2, 2, 2, 2))

    def test_initialization(self):
        s = Style('allowed_name')
        self.assertIsNotNone(s.font)
        self.assertIsNotNone(s.text)
        self.assertIsNotNone(s.box)
        self.assertRaises(ValueError, lambda: Style('bad name'))
        self.assertRaises(ValueError, lambda: Style('1badname'))

    def test_to_definition_default(self):
        self.assertEqual('text-color:black text-opacity:1 text-align:left text-indent:0 '
                         'font-family:Helvetica font-size:12 font-style:normal '
                         'border:none border-opacity:1 border-width:1 '
                         'background:none background-opacity:1 '
                         'margin:0 padding:2', Defaults.default.to_definition())

    def test_to_definition_empty(self):
        self.assertEqual('inherit:default', Style('test', 'default').to_definition())

    def test_round_trip_for_default(self):
        base = Defaults.default
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
        self.assertEqual('font-family:Symbol', style.set('font-font', "Symbol").to_definition())
        self.assertEqual("font-family:'A Font'", style.set('font-font', "A Font").to_definition())

        style = Style('test')
        self.assertEqual('font-size:1', style.set('font-size', '1.0').to_definition())
        self.assertEqual('font-size:2', style.set('fontSize', '2').to_definition())
        self.assertEqual('font-size:2 font-style:bold', style.set('bold', None).to_definition())

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
        self.assertEqual('text-color:purple text-opacity:1', style.set('textOpacity', '1').to_definition())
        self.assertEqual('text-color:purple text-opacity:0.4', style.set('opacity', '40%').to_definition())

        style = Style('test')
        self.assertEqual('background:green', style.set('box-color', 'green').to_definition())
        self.assertEqual('background:red', style.set('box-background', 'red').to_definition())

        style = Style('test')
        self.assertEqual('background-opacity:0.1', style.set('box-opacity', '0.1').to_definition())
        self.assertEqual('background-opacity:0.8', style.set('box-backgroundOpacity', '80%').to_definition())

        style = Style('test')
        self.assertEqual('border:green', style.set('border', 'green').to_definition())
        self.assertEqual('border:red', style.set('box-border', 'red').to_definition())
        self.assertEqual('border:orange', style.set('border-color', 'orange').to_definition())
        self.assertEqual('border:yellow', style.set('box-border-color', 'yellow').to_definition())

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
        self.assertEqual("padding:'7 0.5in'", style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual("margin:'3 2 7 0.5in' padding:'7 0.5in'", style.set('margin', '3 2 7 0.5in').to_definition())

        style = Style('test')
        self.assertEqual('padding:2in', style.set('padding', '2in').to_definition())
        self.assertEqual("padding:'7 0.5in'", style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual("padding:'3 2 7 0.5in'", style.set('box-padding', '3 2 7 0.5in').to_definition())

        style = Style('test')
        self.assertEqual('padding:2in', style.set('padding', '2in').to_definition())
        self.assertEqual("padding:'7 0.5in'", style.set('box-padding', '7 0.5in').to_definition())
        self.assertEqual("padding:'3 2 7 0.5in'", style.set('box-padding', '3 2 7 0.5in').to_definition())

    def test_bad_settings(self):
        style = Style('test')
        with warnings.catch_warnings(record=True) as warning_messages:
            style.set('unknown', 'red')
            self.assertEqual(1, len(warning_messages))
            self.assertEqual("Unknown attribute 'unknown' defined for style 'test'. Ignoring the definition",
                             str(warning_messages[0].message))

        with warnings.catch_warnings(record=True) as warning_messages:
            style.set('color', 'a strange hue')
            self.assertEqual(1, len(warning_messages))
            self.assertEqual("For attribute 'color' of style 'test': Invalid color value 'a strange hue'."
                             " Ignoring the definition", str(warning_messages[0].message))

        with warnings.catch_warnings(record=True) as warning_messages:
            style.set('opacity', '2')
            self.assertEqual(1, len(warning_messages))
            self.assertEqual("For attribute 'opacity' of style 'test': "
                             "Opacity must be in the range [0,1] or [0%, 100%]. Ignoring the definition",
                             str(warning_messages[0].message))

        with warnings.catch_warnings(record=True) as warning_messages:
            style.set('box-opacity', '-1')
            self.assertEqual(1, len(warning_messages))
            self.assertEqual("For attribute 'box-opacity' of style 'test': "
                             "Opacity must be in the range [0,1] or [0%, 100%]. Ignoring the definition",
                             str(warning_messages[0].message))

    def test_box_style_has_border(self):
        self.assertFalse(BoxStyle(border_color='none', border_opacity=1, width=1).has_border())
        self.assertFalse(BoxStyle(border_color='red', border_opacity=1, width=0).has_border())
        self.assertTrue(BoxStyle(border_color='red', border_opacity=1, width=1).has_border())
        self.assertTrue(BoxStyle(border_color='red', border_opacity=0, width=1).has_border())

    def test_box_style_inset_within_margin(self):
        style = BoxStyle(
            margin=Spacing(100, 200, 300, 400),
            padding=Spacing(30, 40, 50, 60),
            width=3, border_color='red'
        )
        base = Rect(1000, 10000, 2000, 20000)
        self.assertEqual(Rect(1100, 9800, 2300, 19600), style.inset_within_margin(base))
        self.assertEqual(Extent(8700, 17300), style.inset_within_margin(base.extent))

    def test_box_style_inset_within_padding(self):
        style = BoxStyle(
            margin=Spacing(100, 200, 300, 400),
            padding=Spacing(30, 40, 50, 60),
            width=3, border_color='red'
        )
        base = Rect(1000, 10000, 2000, 20000)
        self.assertEqual(Rect(1133, 9757, 2353, 19537), style.inset_within_padding(base))
        self.assertEqual(Extent(9000 - 300 - 70 - 6, 18000 - 700 - 110 - 6), style.inset_within_padding(base.extent))

    def test_box_style_outset_to_border(self):
        style = BoxStyle(
            margin=Spacing(100, 200, 300, 400),
            padding=Spacing(30, 40, 50, 60),
            width=3, border_color='red'
        )
        base = Rect(1000, 2000, 3000, 4000)
        self.assertEqual(Rect(967, 2043, 2947, 4063), style.outset_to_border(base))

    def test_box_style_outset_to_margin(self):
        style = BoxStyle(
            margin=Spacing(100, 200, 300, 400),
            padding=Spacing(30, 40, 50, 60),
            width=3, border_color='red'
        )
        base = Rect(1000, 2000, 3000, 4000)
        self.assertEqual(Rect(867, 2243, 2647, 4463), style.outset_to_margin(base))

    def test_box_inset_outset_round_trips(self):
        style = BoxStyle(
            margin=Spacing(100, 200, 300, 400),
            padding=Spacing(30, 40, 50, 60),
            width=3, border_color='red'
        )
        r = Rect(1000, 2000, 3000, 4000)
        self.assertEqual(r, style.outset_to_margin(style.inset_within_padding(r)))
        self.assertEqual(r, style.inset_within_padding(style.outset_to_margin(r)))

        # If we go all the way into the padding, then back out to border -- that's the same as into the margin
        self.assertEqual(style.inset_within_margin(r), style.outset_to_border(style.inset_within_padding(r)))


class TestMakeCompleteStyles(TestCase):

    def test_simple_inheritance(self):
        input = {'default': Defaults.default,
                 'test': Style('test').set('margin', '1in')
                 }
        output = make_complete_styles(input)

        # All the default styles are added in
        self.assertEqual(len(output), 7)

        # Default points to '#default' as parent
        self.assertEqual('#default', output['default'].parent)
        self.assertIsNot(output['default'], input['default'])

        # test inherits some parts, but has overrides
        self.assertEqual(output['test'].text, input['default'].text)
        self.assertEqual(output['test'].font, input['default'].font)
        self.assertEqual(output['test'].box.margin, Spacing(72, 72, 72, 72))

    def test_override_default_style(self):
        input = dedent(
            '''
                    Block Title

                    - content a
                    - content b

                    .. styles::
                       default: 
                         font-family:Courier
            '''
        )
        sheet = text_to_sheet(input)
        styles = make_complete_styles(sheet.styles)
        block = sheet.children[0]
        self.assertEqual('Courier', styles[block.options.title_style].font.family)
        self.assertEqual('Courier', styles[block.options.style].font.family)