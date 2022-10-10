import math
import warnings
from dataclasses import dataclass
from typing import Union

from sly import Parser

from .lexer import CalcLexer
from .var import Variable

class Command:
    type: str
    params: list[Variable]

    def __init__(self, type, *args):
        self.type=type
        self.params = list(args)

    def execute(self, variables:dict):
        if self.type == 'NONE':
            pass
        elif self.type == 'SET':
            variables[self.params[0]] = self.params[1]
        else:
            raise NotImplementedError(self.type)


# noinspection PyUnresolvedReferences
class CalcParser(Parser):
    """
            PARSER.
            command:      VAR = expression
            Expression:     End form of a term
            Term:           Built from terms and factors
            Factor:         Lowest level bits

    """
    variables: dict[str, Variable]

    def __init__(self):
        super().__init__()
        self.variables = {}

    # Get the token list from the lexer (required)
    tokens = CalcLexer.tokens

    # noinspection PyUnresolvedReferences
    precedence = (
        ('left', SEMICOLON),
        ('left', ASSIGN),
        ('left', COMMA),
        ('right', WHEN, THEN),
        ('nonassoc', EQ, NE, LT, LE, GT, GE),
        ('left', PLUS, MINUS),
        ('left', TIMES, DIVIDE),
        ('right', UMINUS),
        ('left', POWER),
    )

    @_('statement SEMICOLON statement')
    def statement(self, p):
        pass

    @_('command')
    def statement(self, p):
        p.command.execute(self.variables)


    @_('VAR ASSIGN expression')
    def command(self, p):
        return Command('SET', p.VAR, p.expression)

    @_('term')
    def expression(self, p):
        return p.term

    @_('factor')
    def term(self, p):
        return p.factor

    # Decisions ####################################################

    @_('WHEN expression THEN command')
    def command(self, p):
        if p.expression:
            return p.command
        else:
            return Command('NONE')


    # Operators ####################################################

    @_('expression PLUS term')
    def expression(self, p):
        return p.expression + p.term

    @_('expression MINUS term')
    def expression(self, p):
        return p.expression - p.term

    @_('term TIMES factor')
    def term(self, p):
        return p.term * p.factor

    @_('term DIVIDE factor')
    def term(self, p):
        return p.term / p.factor

    @_('MINUS factor %prec UMINUS')
    def factor(self, p):
        return -p.factor

    @_('term POWER factor')
    def term(self, p):
        return p.term ** p.factor

    # arguments ####################################################

    @_('expression COMMA expression')
    def args(self, p):
        return [p.expression0, p.expression1]

    @_('expression COMMA args')
    def args(self, p):
        return [p.expression] + p.args

    @_('args COMMA expression')
    def args(self, p):
        return p.args + [p.expression]

    @_('args COMMA args')
    def args(self, p):
        return p.args0 + p.args1

    # Predicates ####################################################

    @_('expression EQ expression')
    def expression(self, p):
        return Variable(p.expression0 == p.expression1)

    @_('expression NE expression')
    def expression(self, p):
        return Variable(p.expression0 != p.expression1)

    @_('expression LE expression')
    def expression(self, p):
        return Variable(p.expression0 <= p.expression1)

    @_('expression LT expression')
    def expression(self, p):
        return Variable(p.expression0 < p.expression1)

    @_('expression GT expression')
    def expression(self, p):
        return Variable(p.expression0 > p.expression1)

    @_('expression GE expression')
    def expression(self, p):
        return Variable(p.expression0 >= p.expression1)

    # Functions ####################################################


    @_('JOIN LPAREN args RPAREN')
    def factor(self, p):
        return Variable(''.join(str(x) for x in p.args))

    @_('MIN LPAREN args RPAREN')
    def factor(self, p):
        return Variable(min(x for x in p.args))

    @_('MAX LPAREN args RPAREN')
    def factor(self, p):
        return Variable(max(x for x in p.args))

    @_('MIDDLE LPAREN args RPAREN')
    def factor(self, p):
        sequence = sorted(x for x in p.args)
        n = len(sequence)
        return Variable(sequence[(n-1) // 2])

    @_('AVERAGE LPAREN args RPAREN')
    def factor(self, p):
        n = len(p.args)
        return Variable(sum(float(x) for x in p.args) / n)

    @_('LENGTH LPAREN expression RPAREN')
    def factor(self, p):
        return Variable(len(str(p.expression)))

    @_('TRUNCATE LPAREN expression RPAREN')
    def factor(self, p):
        return Variable(math.floor(float(p.expression)))

    @_('CEILING LPAREN expression RPAREN')
    def factor(self, p):
        return Variable(math.ceil(float(p.expression)))

    @_('ROUND LPAREN expression RPAREN')
    def factor(self, p):
        return Variable(round(float(p.expression)))

    @_('ROUND LPAREN expression COMMA expression RPAREN')
    def factor(self, p):
        return Variable(round(float(p.expression0), int(p.expression1)))

    @_('LPAREN expression RPAREN')
    def factor(self, p):
        return p.expression

    # Simple Factors ###############################################

    @_('VAR')
    def factor(self, p):
        try:
            return self.variables[p.VAR]
        except KeyError:
            warnings.warn(f"Variable '{p.VAR}' was not defined when it was used. Using zero")
            return Variable(0)

    @_('NUMBER')
    def factor(self, p):
        return Variable(float(p.NUMBER))

    @_('STRING1')
    def factor(self, p):
        # Remove the quotes
        return Variable(p.STRING1[1:-1])

    @_('STRING2')
    def factor(self, p):
        # Remove the quotes
        return Variable(p.STRING2[1:-1])

    @_('TRUE')
    def factor(self, p):
        return Variable(True)

    @_('FALSE')
    def factor(self, p):
        #  the quotes
        return Variable(False)

    def initialize_variables(self, variables: dict[str, Union[str, int, float]]):
        self.variables.clear()
        for k, v in variables.items():
            if isinstance(v, Variable):
                self.variables[k] = v
            else:
                self.variables[k] = Variable(v)
