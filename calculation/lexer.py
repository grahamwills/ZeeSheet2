from sly import Lexer


class CalcLexer(Lexer):
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    tokens = {VAR, NUMBER, STRING1, STRING2,
              TRUE, FALSE,
              EQ, NE, LT, LE, GT, GE,
              PLUS, MINUS, TIMES, POWER, DIVIDE,
              ASSIGN, LPAREN, RPAREN,
              WHEN, THEN,
              MIN, MAX, MIDDLE, AVERAGE, JOIN,
              LENGTH, TRUNCATE, CEILING, ROUND,
              SEMICOLON, COMMA}

    # String containing ignored characters between tokens
    ignore = ' \t'

    # Regular expression rules for tokens
    STRING1 = r'"([^"]*)"'
    STRING2 = r"'([^']*)'"
    VAR = r'[a-z_][a-z0-9_]*'
    NUMBER = r'(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?'

    TRUE = r'TRUE'
    FALSE = r'FALSE'

    # Functions
    LENGTH = r'(LENGTH)|(LEN)'
    TRUNCATE = r'(TRUNCATE)|(FLOOR)|(INT)'
    CEILING = r'(CEILING)|(CEIL)'
    ROUND = r'ROUND'

    MIN = r'MIN'
    MAX = r'MAX'
    MIDDLE = r'(MIDDLE)|(MEDIAN)|(MID)'
    AVERAGE = r'(AVERAGE)|(AVG)|(MEAN)'
    JOIN = r'(JOIN)|(CAT)|(CONCAT)|(CONCATENATE)'

    WHEN = r'(WHEN)|(IF)'
    THEN = r'THEN'

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


    SEMICOLON = r'[;\n]+'
    COMMA = r','


if __name__ == '__main__':
    data = 'x = 3 + 42 * (s - t)'
    lexer = CalcLexer()
    for tok in lexer.tokenize(data):
        print('type=%r, value=%r' % (tok.type, tok.value))
