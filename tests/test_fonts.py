import unittest

from generate.fonts import FontLibrary


class TestFonts(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.LIBRARY = FontLibrary()

    def test_builtin_fonts(self):
        info = self.LIBRARY.get_font('Courier', 14)
        self.assertAlmostEqual(8.81, info.ascent, places=2)
        self.assertAlmostEqual(2.20, info.descent, places=2)

    def test_builtin_fonts_times(self):
        info = self.LIBRARY.get_font('Times', 14)
        self.assertAlmostEqual(9.56, info.ascent, places=2)
        self.assertAlmostEqual(3.04, info.descent, places=2)
        self.assertAlmostEqual(64.16, info.width('hello world'), places=2)
        self.assertAlmostEqual(67.28, info.modify(bold=True).width('hello world'), places=2)

    def test_font_with_only_one_variant(self):
        info = self.LIBRARY.get_font('Rochester', 14)
        self.assertAlmostEqual(14.42, info.ascent, places=2)
        self.assertAlmostEqual(3.61, info.descent, places=2)
        self.assertAlmostEqual(50.11, info.width('hello world'), places=2)
        self.assertAlmostEqual(50.11, info.modify(bold=True).width('hello world'), places=2)
        self.assertAlmostEqual(50.11, info.modify(italic=True).width('hello world'), places=2)
        self.assertAlmostEqual(50.11, info.modify(italic=True, bold=True).width('hello world'), places=2)

    def test_font_with_multiple_single_files(self):
        info = self.LIBRARY.get_font('Arvo', 14)
        self.assertAlmostEqual(10.64, info.ascent, places=2)
        self.assertAlmostEqual(3.22, info.descent, places=2)
        self.assertAlmostEqual(77.20, info.width('hello world'), places=2)
        self.assertAlmostEqual(83.54, info.modify(bold=True).width('hello world'), places=2)
        self.assertAlmostEqual(77.69, info.modify(italic=True).width('hello world'), places=2)
        self.assertAlmostEqual(81.49, info.modify(italic=True, bold=True).width('hello world'), places=2)

    def test_library_has_regular_font_for_all(self):
        for family in self.LIBRARY.content.values():
            font_file = self.LIBRARY.font_file(family.name)
            self.assertIsNotNone(font_file, 'Searching for regular font for: ' + family.name)

    def test_library_has_many_bolds(self):
        different = 0
        for family in self.LIBRARY.content.values():
            reg_file = self.LIBRARY.font_file(family.name)
            bold_file = self.LIBRARY.font_file(family.name, is_bold=True)
            if reg_file != bold_file:
                different += 1
        self.assertTrue(different > 625, f'Only found {different} bold version')

    def test_library_has_several_italics(self):
        different = 0
        for family in self.LIBRARY.content.values():
            reg_file = self.LIBRARY.font_file(family.name)
            bold_file = self.LIBRARY.font_file(family.name, is_italic=True)
            if reg_file != bold_file:
                different += 1
        self.assertTrue(different > 260, f'Only found {different} italic version')

    def test_library_has_several_bold_italics(self):
        different = 0
        for family in self.LIBRARY.content.values():
            reg_file = self.LIBRARY.font_file(family.name)
            bold_file = self.LIBRARY.font_file(family.name, is_italic=True, is_bold=True)
            if reg_file != bold_file:
                different += 1
        self.assertTrue(different > 210, f'Only found {different} bold italic version')

    def test_library_values_match_keys(self):
        for family in self.LIBRARY.content.values():
            self.assertTrue(len(self.LIBRARY[family.name].faces) > 0)

    def test_library(self):
        self.assertTrue(len(self.LIBRARY) > 1400)
        family = self.LIBRARY['IBM PLEX SANS']
        self.assertEqual('IBM Plex Sans', family.name)
        self.assertEqual('sans-serif', family.category)
        self.assertEqual('Bold BoldItalic ExtraLight ExtraLightItalic Italic Light LightItalic Medium MediumItalic '
                         'Regular SemiBold SemiBoldItalic Thin ThinItalic', " ".join(v for v in family.faces.keys()))

    def test_library_with_near_name(self):
        pass
