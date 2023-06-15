import textwrap
import unittest

import main
from structure import BlockOptions
from structure.operations import prepare_for_visit
from . import util


class PrettifyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        cls.items = util.test_data()

    def test_container_options_str(self):
        c = BlockOptions(title='T', style='S')
        self.assertEqual("BlockOptions(style='S', "
                         "image=0, image_mode='normal', image_width=None, "
                         "image_height=None, image_anchor=None, image_brightness=1.0, image_contrast=1.0, "
                         "method='table', equal=False, title='T', title_style=None, bold=None, "
                         "italic=None, title_bold=None, title_italic=None, spacing=2)",
                         str(c))

    def test_prettify(self):
        self.maxDiff = 2000
        for idx, (name, (source, expected)) in enumerate(self.items.items()):
            with self.subTest(f'Prettify example #{idx}', name=name):
                doc = main.Document(source)
                self.assertEqual(expected, doc.prettified(width=80))

    def test_prepare_adds_spaces_around_transition(self):
        input = textwrap.dedent(
            """
                hello
                -------     
                world
                  --
                --9
            """
        )
        expected = textwrap.dedent(
            """
                hello
                
                ----------------
                
                world
                  --
                --9
            """
        )
        output = prepare_for_visit(input)
        self.assertEqual(output, expected)