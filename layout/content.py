from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Iterable

from common import Extent, Point, Rect
from common import configured_logger
from generate.pdf import TextSegment, PDF
from structure.style import Style

LOGGER = configured_logger(__name__)


@dataclass
class Error:
    """ Error from placing one or more items. """
    clipped: float  # Approximate pixel size of items clipped out and lost
    bad_breaks: int  # Measures the error we want to improve above all (counts of bad breaks)
    breaks: int  # Measures error we'd prefer to reduce if possible (counts of line breaks)
    unused_horizontal: float  # Extra horizontal space that has not been used

    def __str__(self):
        return f"Error({self.clipped:1.1f} • {self.bad_breaks} • {self.breaks} • {self.unused_horizontal:1.1f})"

    def __round__(self, n=None):
        return Error(round(self.clipped, n), round(self.bad_breaks, n), round(self.breaks, n),
                     round(self.unused_horizontal, n))

    @classmethod
    def aggregate(cls, mix: Iterable[Error]) -> Optional[Error]:
        items = [i for i in mix if i is not None]
        if not items:
            return None
        c = sum(i.clipped for i in items)
        b = sum(i.bad_breaks for i in items)
        a = sum(i.breaks for i in items)
        u = min(i.unused_horizontal for i in items if i.unused_horizontal > -1)
        return Error(c, b, a, u)

    def better(self, other: Error, ignore_unused: bool = False):
        if self.clipped != other.clipped:
            return self.clipped < other.clipped
        if self.bad_breaks != other.bad_breaks:
            return self.bad_breaks < other.bad_breaks
        if self.breaks != other.breaks:
            return self.breaks < other.breaks
        if ignore_unused:
            return False
        else:
            return self.unused_horizontal < other.unused_horizontal


@dataclass
class PlacedContent:
    extent: Extent  # The size we made it
    location: Point  # Where it was placed within the parent
    error: Optional[Error]  # How bad the placement was

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

    @classmethod
    def from_items(cls, items: List[PlacedContent], extent: Extent = None) -> PlacedGroupContent:
        error = Error.aggregate(i.error for i in items)
        if extent is None:
            r = Rect.union(i.bounds for i in items)
            extent = r.extent
        return PlacedGroupContent(extent, Point(0, 0), error, items)

    def _draw(self, pdf: PDF):
        for p in self.group:
            p.draw(pdf)


@dataclass
class PlacedRunContent(PlacedContent):
    segments: List[TextSegment]  # base text pieces
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        pdf.draw_text(self.style, self.segments)

    def offset_content(self, dx: float):
        off = Point(dx, 0)
        for s in self.segments:
            s.offset = s.offset + off


@dataclass
class PlacedRectContent(PlacedContent):
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)


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
