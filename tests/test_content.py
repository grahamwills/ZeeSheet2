import unittest

from layout.content import Error


class ContentTest(unittest.TestCase):

    def test_error(self):
        e1 = Error(3.0, 4.0, 5.125)
        self.assertEqual('Error(3.0, 4.0 • 5.12)', str(e1))
        e2 = Error(5, 6, 7)
        self.assertEqual(Error(8.0, 10.0, 12.125), Error.sum(e1, e2))
