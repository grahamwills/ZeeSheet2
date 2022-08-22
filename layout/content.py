from __future__ import annotations

import reprlib
from dataclasses import dataclass
from typing import List, Iterable, Tuple, Optional, Any

from common.geom import Extent, Point, Rect
from generate.pdf import TextSegment, PDF
from rst.structure import Run, StructureComponent


@dataclass
class Error:
    """ Error from placing one or more items"""
    unacceptable: float  # Measures the error we want to improve above all
    acceptable: float  # Measures error we'd prefer to reduce if possible
    extra: float  # Extra space that this is not using

    def __str__(self):
        return f"Error({self.unacceptable:1.3}, {self.acceptable:1.3} • {self.extra:1.3})"

    def __add__(self, other: Error):
        return Error(self.unacceptable + other.unacceptable,
                     self.acceptable + other.acceptable,
                     self.extra + other.extra)

    def _score(self) -> float:
        return self.unacceptable * 100 + self.acceptable + self.extra * 1e-6

    @classmethod
    def sum(cls, *args):
        mix = list(args[0]) if len(args) == 1 else list(args)
        u = sum(i.unacceptable for i in mix)
        a = sum(i.acceptable for i in mix)
        e = sum(i.extra for i in mix)
        return Error(u, a, e)

    def better(self, other: Error):
        return self._score() < other._score()


@dataclass
class PlacedContent:
    represents: Any   # Whatever this represents
    extent: Extent  # The size we made it
    location: Point  # Where it was placed within the parent
    error: Error  # How bad the placement was

    @property
    def bounds(self):
        return Rect(self.location.x,
                    self.location.x + self.extent.width,
                    self.location.y,
                    self.location.y + self.extent.height)

    def better(self, other: PlacedContent):
        """Is our placement better?"""
        return other is None or self.error.better(other.error)

    def draw(self, pdf:PDF):
        raise NotImplementedError('Must be defined in subclass')

    def name(self):
        try:
            return self.represents.name()
        except AttributeError:
            return str(self.represents)


@dataclass
class PlacedGroupContent(PlacedContent):
    placed_group: List[PlacedContent] = None

    @classmethod
    def from_items(cls, represents, items: Iterable[PlacedContent], actual: Extent, extra_unused: int) -> PlacedGroupContent:
        placed = list(items)
        bounds = Rect.union(i.bounds for i in placed)
        assert bounds.left >= 0
        assert bounds.top >= 0
        error = Error.sum(i.error for i in placed) + Error(0, 0, extra_unused)
        return PlacedGroupContent(represents, actual, Point(0, 0), error, placed)

    def draw(self, pdf:PDF):
        for p in self.placed_group:
            p.draw(pdf)


@dataclass
class PlacedRunContent(PlacedContent):
    segments: List[TextSegment]  # base text pieces

    def draw(self, pdf:PDF):
        pdf.draw_text(self.segments, self.location)
