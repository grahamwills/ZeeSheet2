import unittest

import main.main
import structure
from structure.model import ContainerOptions
from . import util


class PrettifyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def test_container_options_str(self):
        c = ContainerOptions('T', 'S')
        self.assertEqual("ContainerOptions(title='T', style='S', columns=1, title_style='default-title', "
                         "image=0, image_mode='normal', image_width=None, image_height=None, image_anchor=None)",
                         str(c))

    def test_prettify(self):
        for idx, (name, (source, expected)) in enumerate(self.items.items()):
            with self.subTest(f'Prettify example #{idx}', name=name):
                sheet = main.main.text_to_sheet(source)
                self.assertEqual(expected, main.main.prettify(sheet, 80))
