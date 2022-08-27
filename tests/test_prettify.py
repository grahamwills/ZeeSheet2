import unittest

import structure
from . import util


class PrettifyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def test_prettify(self):
        for idx, (name, (source, expected)) in enumerate(self.items.items()):
            with self.subTest(f'Prettify example #{idx}', name=name):
                sheet = structure.text_to_sheet(source)
                self.assertEqual(structure.prettify(sheet, 80), expected)
