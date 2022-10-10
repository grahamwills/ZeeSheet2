import math
import unittest

from calculation import Variable, Calculator

N1 = Variable(1)
NPI = Variable(3.1415926535)
NM = Variable(-2)

S0 = Variable('')
S1 = Variable('One')
SA = Variable('Aye')
SLONG = Variable('Aye One sees One more')

BF = Variable(False)
BT = Variable(True)


class CalculatorTests(unittest.TestCase):
    VARS = {'a': 5, 'pi': 3.1415926535, 'tr': True, 'fa': False, 's': 's', 't': 'seven slimy serpents'}
    calc: Calculator

    def setUp(self) -> None:
        self.calc = Calculator(self.VARS)

    def test_newlines(self):
        self.calc.evaluate('a =10 \n b=2 \n\n c=a+b')
        self.assertEqual('12', self.calc.var('c'))

    def test_when(self):
        self.calc.evaluate('v1="bar"; WHEN a < 7 THEN v1 = "foo"')
        self.calc.evaluate('v2="bar"; WHEN a > 7 THEN v2 = "foo"')

        self.assertEqual('foo', self.calc.var('v1'))
        self.assertEqual('bar', self.calc.var('v2'))

    def test_predicates(self):
        self.calc.evaluate('v1 = a < a')
        self.calc.evaluate('v2 = a <= a')
        self.calc.evaluate('v3 = a ≤ pi')
        self.calc.evaluate('v4 = 3 == 9/3')
        self.calc.evaluate('v5 = "foo" == TRUE')
        self.calc.evaluate('v6 = FALSE == "foo"')

        self.assertEqual('[O]', self.calc.var('v1'))
        self.assertEqual('[X]', self.calc.var('v2'))
        self.assertEqual('[O]', self.calc.var('v3'))
        self.assertEqual('[X]', self.calc.var('v4'))
        self.assertEqual('[X]', self.calc.var('v5'))
        self.assertEqual('[O]', self.calc.var('v6'))

    def test_join(self):
        self.calc.evaluate('x = JOIN(pi, a, " : ", LEN("abcd"), " ", 7<8, 2**2**2)')
        self.calc.evaluate('y = JOIN(pi, a, " : ", LEN("abcd"), " ", 7<8, 2**2**2) / " "')
        self.assertEqual('3.141595 : 4 [X]16', self.calc.var('x'))
        self.assertEqual('3.141595:4[X]16', self.calc.var('y'))

    def test_simple_functions(self):
        self.calc.evaluate('a = LENGTH(t)')
        self.calc.evaluate('b = LENGTH(pi)')
        self.calc.evaluate('c = TRUNCATE(pi)')
        self.calc.evaluate('d = CEILING(pi)')
        self.calc.evaluate('e = ROUND(pi)')
        self.calc.evaluate('f = ROUND(pi,3)')

        self.assertEqual('20', self.calc.var('a'))
        self.assertEqual('7', self.calc.var('b'))
        self.assertEqual('3', self.calc.var('c'))
        self.assertEqual('4', self.calc.var('d'))
        self.assertEqual('3', self.calc.var('e'))
        self.assertEqual('3.142', self.calc.var('f'))

    def test_multi_argument_functions(self):
        self.calc.evaluate('v1 = MIN(a, pi, LENGTH(t))')
        self.calc.evaluate('v2 = MAX(a, pi, LENGTH(t))')
        self.calc.evaluate('v3 = MIDDLE(a, pi, LENGTH(t))')
        self.calc.evaluate('v4 = AVERAGE(a, pi, LENGTH(t))')

        self.assertEqual('3.14159', self.calc.var('v1'))
        self.assertEqual('20', self.calc.var('v2'))
        self.assertEqual('5', self.calc.var('v3'))
        self.assertEqual('9.38053', self.calc.var('v4'))

    def test_variables(self):
        self.calc.evaluate('x = a * pi')
        self.calc.evaluate('y = x - 15.5')
        self.assertEqual('15.708', self.calc.var('x'))
        self.assertEqual('0.207963', self.calc.var('y'))

    def test_statement(self):
        self.calc.evaluate('x=3; y=10; z=x*y')
        self.calc.evaluate('lvl=3; damage="[" + 4*lvl + "d6 bleeding]"')
        self.assertEqual('30', self.calc.var('z'))
        self.assertEqual('[12d6 bleeding]', self.calc.var('damage'))

    def test_factors(self):
        self.calc.evaluate('a = 5 + 6')
        self.calc.evaluate('b = 5 * 6')
        self.calc.evaluate('c = 5 - 6')
        self.calc.evaluate('d = 5 ** 3')

        self.calc.evaluate('e = "hello" - "l"')
        self.calc.evaluate('f = "hello" / "l"')
        self.calc.evaluate('g = "hello" * 4')
        self.calc.evaluate('h = TRUE * 4')

        self.calc.evaluate('x = -3')

        self.assertEqual('11', self.calc.var('a'))
        self.assertEqual('30', self.calc.var('b'))
        self.assertEqual('-1', self.calc.var('c'))
        self.assertEqual('125', self.calc.var('d'))

        self.assertEqual('helo', self.calc.var('e'))
        self.assertEqual('heo', self.calc.var('f'))
        self.assertEqual('hellohellohellohello', self.calc.var('g'))
        self.assertEqual('4', self.calc.var('h'))

        self.assertEqual('-3', self.calc.var('x'))

    def test_complete_expressions(self):
        self.calc.evaluate('a = (-2**3+1)*(2--3)')
        self.assertEqual('-35', self.calc.var('a'))

    def test_simple_assign(self):
        self.calc.evaluate('fred = 93')
        self.calc.evaluate('wilma = " william \'n\' mary"')
        self.calc.evaluate("wilma2 = '\"will\"iam '")
        self.calc.evaluate("x = 3.14")
        self.calc.evaluate("y = 4.1e4")
        self.calc.evaluate("bool1 = TRUE")
        self.calc.evaluate("bool2 = FALSE")

        self.assertEqual('93', self.calc.var('fred'))
        self.assertEqual(" william 'n' mary", self.calc.var('wilma'))
        self.assertEqual('"will"iam ', self.calc.var('wilma2'))
        self.assertEqual('3.14', self.calc.var('x'))
        self.assertEqual('41000', self.calc.var('y'))
        self.assertEqual('[X]', self.calc.var('bool1'))
        self.assertEqual('[O]', self.calc.var('bool2'))


class VarTests(unittest.TestCase):

    def test_add(self):
        self.assertEqual(2, N1 + N1)
        self.assertEqual(6.283185307, NPI + NPI)
        self.assertEqual(S0, S0 + S0)
        self.assertEqual('OneOne', S1 + S1)
        self.assertEqual(0, BF + BF)
        self.assertEqual(2, BT + BT)

        self.assertEqual('One3.14159', S1 + NPI)
        self.assertEqual('3.14159Aye', NPI + SA)
        self.assertEqual('One[X]', S1 + BT)
        self.assertEqual(2, N1 + BT)

    def test_sub(self):
        self.assertEqual(0, N1 - N1)
        self.assertEqual(0, NPI - NPI)
        self.assertEqual(0, S0 - S0)
        self.assertEqual(0, S1 - S1)
        self.assertEqual(0, BF - BF)
        self.assertEqual(0, BT - BT)

        self.assertEqual(2.1415926535, NPI - N1)
        self.assertEqual(2.1415926535, NPI - S1)
        self.assertEqual(3.1415926535, NPI - S0)

        self.assertEqual('Aye', SA - S1)
        self.assertEqual('Aye  sees One more', SLONG - S1)

    def test_mul(self):
        self.assertEqual(1, N1 * N1)
        self.assertEqual(9.869604400525171, NPI * NPI)
        self.assertEqual(0, S0 * S0)
        self.assertEqual(1, S1 * S1)
        self.assertEqual(0, BF * BF)
        self.assertEqual(1, BT * BT)

        self.assertEqual(3.1415926535, NPI * N1)
        self.assertEqual(3.1415926535, NPI * S1)
        self.assertEqual(0, NPI * S0)

        self.assertEqual('Aye', SA * S1)
        self.assertEqual('', SA * S0)

        self.assertEqual('OneOneOne', S1 * NPI)
        self.assertEqual('', S1 * NM)

    def test_div(self):
        self.assertEqual(1, N1 / N1)
        self.assertEqual(1, NPI / NPI)
        self.assertEqual('', S0 / S0)
        self.assertEqual('', S1 / S1)
        self.assertEqual(1, BF / BF)
        self.assertEqual(1, BT / BT)

        self.assertEqual(-1.57079632675, NPI / NM)
        self.assertEqual(3.1415926535, NPI / S1)
        self.assertEqual(math.inf, NPI / S0)

        self.assertEqual('Aye', SA / S1)
        self.assertEqual('Aye', SA / S0)

        self.assertEqual('Aye', SA / S1)
        self.assertEqual('Aye  sees  more', SLONG / S1)

    def test_mod(self):
        self.assertEqual(0, N1 % N1)
        self.assertEqual(0, NPI % NPI)
        self.assertEqual(1, S0 % S0)
        self.assertEqual(0, S1 % S1)
        self.assertEqual(1, BF % BF)
        self.assertEqual(0, BT % BT)

        self.assertEqual(-0.8584073465, NPI % NM)
        self.assertEqual(0.14159, round(NPI % S1, 5))
        self.assertEqual(math.inf, NPI % S0)

        self.assertEqual(0, SA % S1)
        self.assertEqual(math.inf, SA % S0)
        self.assertEqual(0, SA % S1)

    def test_equal(self):
        self.assertEqual(1, N1)
        self.assertEqual('1', N1)
        self.assertEqual(True, N1)
        self.assertEqual(0, BF)
        self.assertEqual(1.0, BT)
        self.assertEqual(1.0, S1)
        self.assertEqual(0.0, S0)
        self.assertEqual(N1, S1)
        self.assertEqual(BT, S1)
        self.assertEqual(BF, S0)
        self.assertNotEqual(1.1, N1)
        self.assertNotEqual(1.1, S1)
        self.assertNotEqual(1.1, BT)

    def test_less_than(self):
        self.assertLess(NM, N1)
        self.assertGreater(NPI, N1)
        self.assertLess(SA, S1)
        self.assertLess(BF, BT)
        self.assertLess(NM, S0)
        self.assertLess(BF, NPI)

    def test_str(self):
        self.assertEqual('1', str(N1))
        self.assertEqual('3.14159', str(NPI))
        self.assertEqual('', str(S0))
        self.assertEqual('One', str(S1))
        self.assertEqual('[O]', str(BF))
        self.assertEqual('[X]', str(BT))

    def test_float(self):
        self.assertEqual(1, float(N1))
        self.assertEqual(3.1415926535, float(NPI))
        self.assertEqual(0, float(S0))
        self.assertEqual(1, float(S1))
        self.assertEqual(0, float(BF))
        self.assertEqual(1, float(BT))

    def test_round(self):
        self.assertEqual(1, round(N1))
        self.assertEqual(3.0, round(NPI))
        self.assertEqual(0, round(S0))
        self.assertEqual(1, round(S1))
        self.assertIs(BF, round(BF))
        self.assertIs(BT, round(BT))
        self.assertEqual('Aye', round(SLONG))
        self.assertEqual('Aye One s', round(SLONG, 9))

    def test_int(self):
        self.assertEqual(1, int(N1))
        self.assertEqual(3, int(NPI))
        self.assertEqual(0, int(S0))
        self.assertEqual(1, int(S1))
        self.assertEqual(0, int(BF))
        self.assertEqual(1, int(BT))

    def test_bool(self):
        self.assertEqual(True, bool(N1))
        self.assertEqual(True, bool(NPI))
        self.assertEqual(False, bool(S0))
        self.assertEqual(True, bool(S1))
        self.assertEqual(False, bool(BF))
        self.assertEqual(True, bool(BT))

    def test_abs(self):
        self.assertEqual(1, abs(N1))
        self.assertEqual(3.1415926535, abs(NPI))
        self.assertEqual(2, abs(NM))
        self.assertEqual(0, abs(S0))
        self.assertEqual(1, abs(S1))
        self.assertEqual(0, abs(BF))
        self.assertEqual(1, abs(BT))

    def test_neg(self):
        self.assertEqual(-1, -(N1))
        self.assertEqual(-3.1415926535, -(NPI))
        self.assertEqual(2, -(NM))
        self.assertEqual(0, -(S0))
        self.assertEqual('eyA', -(SA))
        self.assertEqual(0, -(BF))
        self.assertEqual(-1, -(BT))
