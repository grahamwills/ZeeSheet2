import warnings

from sly import Lexer


class CalcLexer(Lexer):
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    tokens = {VAR, NUMBER, STRING1, STRING2,
              TRUE, FALSE,
              EQ, NE, LT, LE, GT, GE,
              PLUS, MINUS, TIMES, POWER, DIVIDE,
              ASSIGN, LPAREN, RPAREN,
              WHEN, THEN, ELSE,
              MIN, MAX, MIDDLE, AVERAGE, JOIN, VARIABLE, PLUSMINUS,
              LENGTH, TRUNCATE, CEILING, ROUND,
              SEMICOLON, COMMA}

    # String containing ignored characters between tokens
    ignore = ' \t'
    ignore_comment = r'\#.*\n'

    # Regular expression rules for tokens
    STRING1 = r'"([^"]*)"'
    STRING2 = r"'([^']*)'"
    VAR = r'[a-z_][a-z0-9_]*'
    NUMBER = r'(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?'

    TRUE = r'TRUE'
    FALSE = r'FALSE'

    # Functions
    PLUSMINUS = r'(PLUSMINUS)|(±)'
    LENGTH = r'(LENGTH)|(LEN)'
    TRUNCATE = r'(TRUNCATE)|(FLOOR)|(INT)'
    CEILING = r'(CEILING)|(CEIL)'
    ROUND = r'ROUND'
    MIN = r'MIN'
    MAX = r'MAX'
    MIDDLE = r'(MIDDLE)|(MEDIAN)|(MID)'
    AVERAGE = r'(AVERAGE)|(AVG)|(MEAN)'
    JOIN = r'(JOIN)|(CAT)|(CONCAT)|(CONCATENATE)'
    VARIABLE = r'(VARIABLE)|(VAR)'

    WHEN = r'(WHEN)|(IF)'
    THEN = r'THEN'
    ELSE = r'ELSE'

    EQ = r'=='
    NE = r'!='
    LE = r'(<=)|≤'
    GE = r'(>=)|≥'
    LT = r'<'
    GT = r'>'

    POWER = r'\*\*'
    PLUS = r'\+'
    MINUS = r'-'
    TIMES = r'\*'
    DIVIDE = r'/'

    ASSIGN = r'='
    LPAREN = r'\('
    RPAREN = r'\)'

    COMMA = r','

    # Semicolons and newlines separate statements
    @_(r'[;\n]+')
    def SEMICOLON(self, t):
        self.lineno += sum(1 if c == '\n' else 0 for c in t.value)
        return t

    # Error handling rule
    def error(self, t):
        warnings.warn(f"Illegal character '{t.value[0]}' at line number {t.lineno}")
        while True:
            self.index += 1
            if self.index == len(self.text):
                break
            if self.text[self.index] in ';\n':
                self.index += 1
                break


if __name__ == '__main__':
    data = 'x = 3 + 42 * (s - t)'
    lexer = CalcLexer()
    for tok in lexer.tokenize(data):
        print('type=%r, value=%r' % (tok.type, tok.value))
