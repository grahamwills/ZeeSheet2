from unittest import TestCase

from converters.dnd4e import read_dnd4e, read_rules_elements
from main import Document


class TestCommon(TestCase):

    def process(self, name: str):
        data = read_dnd4e(f'tests/samples/{name}.dnd4e', self.rules)
        rst = data.to_rst()
        print(rst)
        doc = Document(rst)
        d = doc.data()
        with open(f'test_{name}.pdf', 'wb') as f:
            f.write(d)

    def setUp(self):
        self.rules = read_rules_elements()

    def test_rules_reading(self):
        self.assertEqual(37568, len(self.rules))

    def test_Crivers(self):
        self.process('Jim - Crivers 7')

    def test_Davars(self):
        self.process('Josh - Davars 7')

    def test_Roisin_New(self):
        self.process('Suzanne - roisin 7')


    def test_nine(self):
        self.process('nine-4')

    def test_roisin(self):
        self.process('roisin-3')

    def test_grumph(self):
        self.process('grumph-6')

    def test_Samantha(self):
        self.process('Samanther')

    def test_sigbert(self):
        self.process('sigbert')

    def test_tharavol(self):
        self.process('tharavol')

    def test_vlon(self):
        self.process('vlon')
