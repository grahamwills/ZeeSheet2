import unittest
from rst.validate import build_structure
from textwrap import dedent

class BasicBlocks(unittest.TestCase):

    def test_empty(self):
        source = ''
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual('', sheet.structure_str())

    def test_one_line(self):
        source = 'hello'
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[hello: ]>", sheet.structure_str())

    def test_two_lines(self):
        source = 'hello\nworld'
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[hello world: ]>", sheet.structure_str())

    def test_two_sections(self):
        source = dedent('''
            one
            header
            
            and another
        ''')
        sheet = build_structure(source)
        self.assertEqual('',  sheet.combined_issues())
        self.assertEqual("<[one header: ] [and another: ]>", sheet.structure_str())