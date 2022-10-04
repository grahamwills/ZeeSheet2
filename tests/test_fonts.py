import unittest
import warnings
import zipfile

from generate import fonts
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
        self.assertAlmostEqual(67.28, info.modify('strong').width('hello world'), places=2)

    def test_font_with_only_one_variant(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', Warning)
            info = self.LIBRARY.get_font('Rochester', 14)
            self.assertAlmostEqual(14.42, info.ascent, places=2)
            self.assertAlmostEqual(3.61, info.descent, places=2)
            self.assertAlmostEqual(50.11, info.width('hello world'), places=2)
            self.assertAlmostEqual(50.11, info.modify('strong').width('hello world'), places=2)
            self.assertAlmostEqual(50.11, info.modify('emphasis').width('hello world'), places=2)

    def test_font_with_multiple_single_files(self):
        info = self.LIBRARY.get_font('Arvo', 14)
        self.assertAlmostEqual(10.64, info.ascent, places=2)
        self.assertAlmostEqual(3.22, info.descent, places=2)
        self.assertAlmostEqual(77.20, info.width('hello world'), places=2)
        self.assertAlmostEqual(83.54, info.modify('strong').width('hello world'), places=2)
        self.assertAlmostEqual(77.69, info.modify('emphasis').width('hello world'), places=2)

    def test_library_has_regular_font_for_all(self):
        for family in self.LIBRARY._families.values():
            font_file = family.match_face_name('regular')
            self.assertIsNotNone(font_file, 'Searching for regular font for: ' + family.name)

    def test_library_has_many_bolds(self):
        different = 0
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', Warning)
            for family in self.LIBRARY._families.values():
                reg_file = family.match_face_name('regular')
                bold_file = family.match_face_name('bold')
                if reg_file != bold_file:
                    different += 1
        self.assertTrue(different > 625, f'Only found {different} bold version')

    def test_library_has_several_italics(self):
        different = 0
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', Warning)
            for family in self.LIBRARY._families.values():
                reg_file = family.match_face_name('regular')
                bold_file = family.match_face_name('italic')
                if reg_file != bold_file:
                    different += 1
        self.assertTrue(different > 260, f'Only found {different} italic version')

    def test_library_has_several_bold_italics(self):
        different = 0
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', Warning)
            for family in self.LIBRARY._families.values():
                reg_file = family.match_face_name('regular')
                bold_file = family.match_face_name('boldItalic')
                if reg_file != bold_file:
                    different += 1
        self.assertTrue(different > 210, f'Only found {different} bold italic version')

    def test_library_values_match_keys(self):
        for family in self.LIBRARY._families.values():
            self.assertTrue(len(self.LIBRARY[family.name].faces) > 0)

    def test_get_font_by_full_name(self):
        f = self.LIBRARY.get_font('Noto Serif Display', 12, 'BoldItalic')
        self.assertEqual('Noto Serif Display-BoldItalic', f.name)

    def test_font_found_by_name_has_other_faces(self):
        f1 = self.LIBRARY.get_font('Georama', 12, 'bold')
        self.assertEqual('Georama-BoldItalic', f1.modify('emphasis').name)

    def test_all_fonts_exist(self):
        all_names = []
        for family in self.LIBRARY._families.values():
            if not family.name.startswith('Noto') and not family.category == 'builtin':
                all_names += family.faces.values()

        last_zip = None
        for name in sorted(all_names):
            if not last_zip:
                zipfile_name = fonts._zipfile(name)
                last_zip = zipfile.ZipFile(zipfile_name.absolute(), 'r')
            try:
                self.assertIsNotNone(last_zip.getinfo(name + '.ttf'))
            except KeyError:
                zipfile_name = fonts._zipfile(name)
                last_zip = zipfile.ZipFile(zipfile_name.absolute(), 'r')
                self.assertIsNotNone(last_zip.getinfo(name + '.ttf'))

    def test_library(self):
        self.assertTrue(len(self.LIBRARY) > 1400)
        family = self.LIBRARY['IBM PLEX SANS']
        self.assertEqual('IBM Plex Sans', family.name)
        self.assertEqual('sans-serif', family.category)
        self.assertEqual('Bold BoldItalic ExtraLight ExtraLightItalic Italic Light LightItalic Medium MediumItalic '
                         'Regular SemiBold SemiBoldItalic Thin ThinItalic', " ".join(v for v in family.faces.keys()))

    def test_families_know_if_they_have_all_faces(self):
        self.assertTrue(self.LIBRARY['IBM PLEX SANS'].contains_standard_faces())
        self.assertTrue(self.LIBRARY['Courier'].contains_standard_faces())
        self.assertFalse(self.LIBRARY['Special Elite'].contains_standard_faces())
        self.assertFalse(self.LIBRARY['Cabin Sketch'].contains_standard_faces())

    def test_similar_names(self):
        self.assertEqual(['Baskervville', 'Libre Baskerville'], self.LIBRARY.similar_names('Baskerville'))
        self.assertEqual(['Freehand'], self.LIBRARY.similar_names('Fredhand'))

    def _faces(self, family: str) -> str:
        fonts = [self.LIBRARY.get_font(family, 12, face) for face in 'Regular Bold Italic BoldItalic'.split()]
        return ' • '.join(f.name.replace(family + '-', '') for f in fonts)

    def test_font_versions(self):
        self.assertEqual('Regular • Bold • MediumItalic • BoldItalic', self._faces('Montserrat'))
