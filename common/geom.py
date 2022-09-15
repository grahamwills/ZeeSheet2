from __future__ import annotations

import math
from collections import namedtuple
from typing import NamedTuple, Union, Tuple


class Spacing(NamedTuple):
    left: float
    right: float
    top: float
    bottom: float

    @property
    def horizontal(self) -> float:
        return self.left + self.right

    @property
    def vertical(self) -> float:
        return self.top + self.bottom

    def __str__(self):
        return "[l=%d, r=%d, t=%d, b=%d]" % self

    def __bool__(self):
        return self.left or self.right or self.top or self.bottom

    def __round__(self, n=None):
        return Spacing(left=round(self.left, n), right=round(self.right, n),
                       top=round(self.top, n), bottom=round(self.bottom, n))

    @classmethod
    def balanced(cls, size: float) -> Spacing:
        return Spacing(size, size, size, size)


class Point(NamedTuple):
    x: float
    y: float

    def __str__(self) -> str:
        x = f"{self.x:.2f}".rstrip('0').rstrip('.')
        y = f"{self.y:.2f}".rstrip('0').rstrip('.')
        return f"({x}, {y})"

    def __add__(self, other) -> Point:
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other) -> Point:
        return Point(self.x - other.x, self.y - other.y)

    def __abs__(self) -> float:
        return (self.x ** 2 + self.y ** 2) ** 0.5

    def __neg__(self) -> Point:
        return Point(-self.x, -self.y)

    def __mul__(self, m) -> Point:
        return Point(m * self.x, m * self.y)

    def __truediv__(self, m) -> Point:
        return Point(self.x / m, self.y / m)

    def __floordiv__(self, m) -> Point:
        return Point(self.x // m, self.y // m)

    def __rmul__(self, m) -> Point:
        return Point(m * self.x, m * self.y)

    def __eq__(self, other) -> bool:
        return self.x == other.x and self.y == other.y

    def __hash__(self) -> int:
        return hash(self.x) + 17 * hash(self.y)

    def __bool__(self) -> bool:
        return self.x != 0 or self.y != 0

    def __round__(self, n=None):
        return Point(round(self.x, n), round(self.y, n))

    def to_polar(self) -> (float, float):
        """ returns θ, d """
        return math.atan2(self.y, self.x), abs(self)

    @classmethod
    def from_polar(cls, θ, d) -> Point:
        return Point(d * math.cos(θ), d * math.sin(θ))


class Extent(NamedTuple):
    width: float
    height: float

    @property
    def area(self):
        return self.width * self.height

    def __round__(self, n=None):
        return Extent(round(self.width, n), round(self.height, n))


class Rect(namedtuple('Rect', 'left right top bottom')):

    @classmethod
    def union(cls, *args) -> Rect:
        mix = list(args[0]) if len(args) == 1 else list(args)
        left = min(r.left for r in mix)
        right = max(r.right for r in mix)
        top = min(r.top for r in mix)
        bottom = max(r.bottom for r in mix)
        return Rect(left, right, top, bottom)

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.bottom - self.top

    @property
    def center(self) -> Point:
        return Point((self.left + self.right) / 2, (self.top + self.bottom) / 2)

    @property
    def extent(self) -> Extent:
        return Extent(self.width, self.height)

    @property
    def perimeter(self) -> float:
        return 2 * self.width + 2 * self.height

    @property
    def area(self) -> float:
        return self.width * self.height

    def __round__(self, n=None):
        return Rect(round(self.left, n), round(self.right, n), round(self.top, n), round(self.bottom, n))

    def __add__(self, off: Union[Spacing, Point, Tuple]) -> Rect:
        try:
            return Rect(self.left - off.left, self.right + off.right,
                        self.top - off.top, self.bottom + off.bottom)
        except AttributeError:
            return Rect(self.left + off[0], self.right + off[0], self.top + off[1], self.bottom + off[1])

    def __sub__(self, off: Union[Spacing, Point, Tuple]) -> Rect:
        try:
            return Rect(self.left + off.left, self.right - off.right,
                        self.top + off.top, self.bottom - off.bottom)
        except AttributeError:
            return Rect(self.left - off[0], self.right - off[0], self.top - off[1], self.bottom - off[1])

    def __str__(self):
        return "[l=%d r=%d t=%d b=%d]" % (self.left, self.right, self.top, self.bottom)
