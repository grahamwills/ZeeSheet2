from __future__ import annotations

import math
import numbers
from dataclasses import dataclass
from enum import Enum
from typing import Any


class VType(Enum):
    NUM = 1
    STR = 2
    BOOL = 3


@dataclass
class Variable:
    value: Any
    type: VType = None

    def __post_init__(self):
        if isinstance(self.value, bool):
            self.type = VType.BOOL
        elif isinstance(self.value, numbers.Number):
            self.value = float(self.value)
            self.type = VType.NUM
        else:
            self.value = str(self.value)
            self.type = VType.STR

    @property
    def isstr(self):
        return self.type == VType.STR

    @property
    def isnum(self):
        return self.type == VType.NUM

    @property
    def isbool(self):
        return self.type == VType.BOOL

    def __eq__(self, other):
        if not isinstance(other, Variable):
            other = Variable(other)
        if self.isnum or other.isnum:
            return float(self) == float(other)
        elif self.isbool or other.isbool:
            return bool(self) == bool(other)
        else:
            return self.value == other.value

    def __lt__(self, other):
        if not isinstance(other, Variable):
            other = Variable(other)
        if self.isnum or other.isnum:
            return float(self) < float(other)
        elif self.isbool or other.isbool:
            return bool(self) < bool(other)
        else:
            return self.value < other.value

    def __le__(self, other):
        return self < other or self == other

    def __add__(self, other: Variable) -> Variable:
        if self.isstr or other.isstr:
            return Variable(str(self) + str(other))
        else:
            return Variable(float(self) + float(other))

    def __sub__(self, other: Variable) -> Variable:
        if self.isstr:
            a = str(self)
            b = str(other)
            return Variable(a.replace(b, '', 1))
        else:
            return Variable(float(self) - float(other))

    def __mul__(self, other: Variable) -> Variable:
        if self.isstr:
            a = str(self)
            return Variable(a * int(other))
        else:
            return Variable(float(self) * float(other))

    def __pow__(self, other: Variable) -> Variable:
        if self.isstr:
            a = str(self)
            return Variable(a * int(other))
        else:
            return Variable(float(self) ** float(other))

    def __truediv__(self, other: Variable) -> Variable:
        if self.isstr:
            a = str(self)
            b = str(other)
            return Variable(a.replace(b, ''))
        else:
            x = float(self)
            y = float(other)
            if y == 0:
                if x == 0:
                    return Variable(1)
                else:
                    return Variable(math.inf if x > 0 else -math.inf)
            else:
                return Variable(x/y)

    def __mod__(self, other: Variable) -> Variable:
        x = float(self)
        y = float(other)
        if y == 0:
            if x ==y:
                return Variable(1)
            else:
                return Variable(math.inf)
        else:
            return Variable(x % y)

    def __round__(self, n=None):
        if self.isstr:
            if n:
                return Variable(self.value[:n])
            else:
                q = str(self).find(' ')
                if q>=0:
                    return Variable(self.value[:q])
                else:
                    return self
        elif self.isbool:
            return self
        else:
            return Variable(round(self.value, n))

    def __neg__(self) -> Variable:
        if self.isstr:
            return Variable(self.value[::-1])
        else:
            return Variable(-float(self))

    def __abs__(self) -> Variable:
        if self.isnum:
            return Variable(abs(self.value))
        else:
            return self

    def __int__(self) -> int:
        try:
            return int(self.value)
        except ValueError:
            return 0 if self.value == '' else 1

    def __bool__(self) -> bool:
        try:
            return bool(self.value)
        except ValueError:
            return self.value != ''

    def __float__(self) -> float:
        try:
            return float(self.value)
        except ValueError:
            return 0.0 if self.value == '' else 1.0

    def __str__(self) -> str:
        if self.isbool:
            return '[X]' if self.value else '[O]'
        elif self.isnum:
            return '{:g}'.format(self.value)
        else:
            return str(self.value)
