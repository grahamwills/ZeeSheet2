import textwrap
from typing import Union

from calculation.lexer import CalcLexer
from calculation.parser import CalcParser


class Calculator:

    def __init__(self, variables: dict[str, Union[str, int, float]]):
        self.lexer = CalcLexer()
        self.parser = CalcParser()
        self.parser.initialize_variables(variables)

    def evaluate(self, text: str):
        text = textwrap.dedent(text).strip()
        tokens = self.lexer.tokenize(text)
        self.parser.parse(tokens)

    def variables(self):
        return {k: str(p) for k, p in self.parser.variables.items()}

    def var(self, name: str):
        try:
            return str(self.parser.variables[name])
        except KeyError:
            return None
