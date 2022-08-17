from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable

from layout.geom import Extent, Point, Rect


@dataclass
class Content:
    pass


@dataclass
class GroupContent(Content):
    content_group: List[Content]


@dataclass
class Error:
    """ Error from placing one or more items"""
    unacceptable: float  # Measures the error we want to improve above all
    acceptable: float  # Measures error we'd prefer to reduce if possible
    extra: float  # Extra space that this is not using

    def __str__(self):
        return f"Error({self.unacceptable:1.3}, {self.acceptable:1.3} • {self.extra:1.3})"

    @classmethod
    def sum(cls, *args):
        mix = list(args[0]) if len(args) == 1 else list(args)
        u = sum(i.unacceptable for i in mix)
        a = sum(i.acceptable for i in mix)
        e = sum(i.extra for i in mix)
        return Error(u, a, e)


@dataclass
class PlacedContent:
    content: Content  # The definition of what goes in here
    requested: Extent  # The size it was asked to be
    actual: Extent  # The size we made it
    location: Point  # Where it was placed within the parent
    error: Error  # How bad the placement was

    @property
    def bounds(self):
        return Rect(self.location.x, self.location.y,
                    self.location.x + self.actual.width,
                    self.location.y + self.actual.height)


@dataclass
class PlacedGroupContent(PlacedContent):
    placed_group: List[PlacedContent]

    @classmethod
    def from_items(cls, items: Iterable[PlacedContent], requested: Extent) -> PlacedGroupContent:
        placed = list(items)
        content = GroupContent([i.content for i in placed])
        bounds = Rect.union(i.bounds for i in placed)
        assert bounds.left >= 0
        assert bounds.top >= 0
        actual = bounds.extent
        error = Error.sum(i.error for i in placed)
        return PlacedGroupContent(content, requested, actual, Point(0, 0), error, placed)