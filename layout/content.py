from __future__ import annotations

import reprlib
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Iterable

from common import Extent, Point, Rect
from common import configured_logger, to_str
from generate.pdf import TextSegment, PDF
from structure.style import Style

LOGGER = configured_logger(__name__)


def _f(v) -> str:
    return to_str(v, places=1)


@dataclass
class PlacementError:
    """ Error from placing one or more items. """
    clipped: float  # Approximate pixel size of items clipped out and lost
    bad_breaks: int  # Measures the error we want to improve above all (counts of bad breaks)
    breaks: int  # Measures error we'd prefer to reduce if possible (counts of line breaks)

    def __str__(self):
        return f"Error({_f(self.clipped)} • {_f(self.bad_breaks)} • {_f(self.breaks)} )"

    def __round__(self, n=None):
        return PlacementError(round(self.clipped, n), round(self.bad_breaks, n), round(self.breaks, n))

    def __bool__(self):
        return self.clipped != 0 or self.bad_breaks != 0

    def __iadd__(self, other: PlacementError):
        self.clipped += other.clipped
        self.bad_breaks += other.bad_breaks
        self.breaks += other.breaks
        return self

    @classmethod
    def aggregate(cls, mix: Iterable[PlacementError]) -> Optional[PlacementError]:
        items = [i for i in mix if i is not None]
        if not items:
            return None
        c = sum(i.clipped for i in items)
        b = sum(i.bad_breaks for i in items)
        a = sum(i.breaks for i in items)
        return PlacementError(c, b, a)

    def compare(self, other):
        if self.clipped != other.clipped:
            return -1 if self.clipped < other.clipped else 1
        if self.bad_breaks != other.bad_breaks:
            return -1 if self.bad_breaks < other.bad_breaks else 1
        # if self.breaks != other.breaks:
        #     return -1 if self.breaks < other.breaks else 1
        return 0

    def better(self, other: PlacementError):
        return self.compare(other) < 0


@dataclass
class PlacedContent:
    extent: Extent  # The size we made it
    location: Point  # Where it was placed within the parent
    error: Optional[PlacementError]  # How bad the placement was

    @property
    def bounds(self):
        return Rect(self.location.x,
                    self.location.x + self.extent.width,
                    self.location.y,
                    self.location.y + self.extent.height)

    def better(self, other: PlacedContent):
        """Is our placement better?"""
        return other is None or self.error.better(other.error)

    def _draw(self, pdf: PDF):
        raise NotImplementedError('Must be defined in subclass')

    def __str__(self):
        return '<bds=' + str(round(self.bounds)) + ", err=" + str(self.error) + '>'

    def draw(self, pdf: PDF):
        pdf.saveState()
        _debug_draw_rect(pdf, self.bounds)
        if self.location:
            pdf.translate(self.location.x, self.location.y)
        self._draw(pdf)
        pdf.restoreState()


@dataclass
class PlacedGroupContent(PlacedContent):
    group: List[PlacedContent] = None
    sum_squares_unused_space: float = None

    @classmethod
    def from_items(cls, items: List[PlacedContent], extent: Extent = None) -> PlacedGroupContent:
        error = PlacementError.aggregate(i.error for i in items)
        if extent is None:
            r = Rect.union(i.bounds for i in items)
            extent = r.extent
        return PlacedGroupContent(extent, Point(0, 0), error, items)

    def better(self, other: PlacedGroupContent):
        """Is our placement better?"""
        if other is None:
            return True
        diff = self.error.compare(other.error)
        if diff == 0:
            if self.sum_squares_unused_space is not None and other.sum_squares_unused_space is not None:
                return self.sum_squares_unused_space < other.sum_squares_unused_space
            else:
                return 0
        else:
            return diff < 0

    def _draw(self, pdf: PDF):
        for p in self.group:
            p.draw(pdf)

    def __str__(self):
        base = super().__str__()
        return base[0] + '#items=' + _f(len(self.group)) + ', ss=' + _f(self.sum_squares_unused_space) + ', ' + base[1:]

    def __copy__(self):
        group = [copy(g) for g in self.group]
        return PlacedGroupContent(self.extent, self.location, self.error, group, self.sum_squares_unused_space)


@dataclass
class PlacedRunContent(PlacedContent):
    segments: List[TextSegment]  # base text pieces
    style: Style  # Style for this item
    effective_width: float  # Pixels of empty space we didn't need

    def _draw(self, pdf: PDF):
        pdf.draw_text(self.style, self.segments)

    def offset_content(self, dx: float):
        off = Point(dx, 0)
        for s in self.segments:
            s.offset = s.offset + off

    def __str__(self):
        base = super().__str__()
        txt = ''.join(s.to_text() for s in self.segments)
        return base[0] + reprlib.repr(txt) + ', effective_width=' + _f(self.effective_width) + ', ' + base[1:]

    def __copy__(self):
        return PlacedRunContent(self.extent, self.location, self.error, self.segments, self.style, self.effective_width)


@dataclass
class PlacedRectContent(PlacedContent):
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)

    def __copy__(self):
        return PlacedRectContent(self.extent, self.location, self.error, self.style)


def _debug_draw_rect(pdf, rect):
    if pdf.debug:
        r, g, b, a = 1, 0, 1, 0.2
        pdf.saveState()
        pdf.setFillColorRGB(r, g, b, alpha=a)
        pdf.setStrokeColorRGB(r, g, b, alpha=a * 2.5)
        pdf._draw_rect(rect, 1, 1)
        pdf.restoreState()


class ExtentTooSmallError(RuntimeError):
    """ The space is too small to fit anything """
    pass


class ItemDoesNotExistError(RuntimeError):
    """ The item requested to be placed does not exist"""
    pass


class ErrorLimitExceededError(RuntimeError):
    """ The accumulated error has exceeded the maximum allowed"""
    pass
