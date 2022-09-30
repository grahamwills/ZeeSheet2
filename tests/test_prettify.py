import textwrap
import unittest

import main
from structure.model import ContainerOptions
from structure.operations import prepare_for_visit
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
                
                -------
                
                world
                  --
                --9
            """
        )
        output = prepare_for_visit(input)
        self.assertEqual(output, expected)
