from __future__ import annotations

from dataclasses import dataclass
from typing import List, Iterable, Any

from common import Extent, Point, Rect
from common import configured_logger
from generate.pdf import TextSegment, PDF, DrawMethod
from structure import Section, Block, Item, Run, description, Sheet
from structure.style import Style

LOGGER = configured_logger(__name__)


@dataclass
class Error:
    """ Error from placing one or more items. """
    clipped: float  # Approximate pixel size of items clipped out and lost
    bad_breaks: float  # Measures the error we want to improve above all (counts of bad breaks)
    breaks: float  # Measures error we'd prefer to reduce if possible (counts of line breaks)
    extra: float  # Extra space that this is not using (in pixels)

    def __str__(self):
        return f"Error({self.bad_breaks:1.3}, {self.breaks:1.3} • {self.extra:1.3})"

    def __add__(self, other: Error):
        return Error(self.clipped + other.clipped,
                     self.bad_breaks + other.bad_breaks,
                     self.breaks + other.breaks,
                     self.extra + other.extra)

    def __round__(self, n=None):
        return Error(round(self.clipped, n), round(self.bad_breaks, n), round(self.breaks, n), round(self.extra, n))

    def _score(self) -> float:
        return self.clipped * 1e6 + self.bad_breaks * 100 + self.breaks + self.extra * 1e-6

    @classmethod
    def sum(cls, *args):
        mix = list(args[0]) if len(args) == 1 else list(args)
        c = sum(i.clipped for i in mix)
        u = sum(i.bad_breaks for i in mix)
        a = sum(i.breaks for i in mix)
        e = sum(i.extra for i in mix)
        return Error(c, u, a, e)

    def better(self, other: Error):
        return self._score() < other._score()


@dataclass
class PlacedContent:
    represents: Any  # Whatever this represents
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

    def _draw(self, pdf: PDF):
        raise NotImplementedError('Must be defined in subclass')

    def name(self):
        try:
            return description(self.represents, short=True)
        except AttributeError:
            return str(self.represents)

    def draw(self, pdf: PDF):
        pdf.saveState()
        _debug_draw_rect(pdf, self.represents, self.bounds)
        if self.location:
            LOGGER.debug(self.name() + ': Translating by ' + str(self.location))
            pdf.translate(self.location.x, self.location.y)
        self._draw(pdf)
        pdf.restoreState()


@dataclass
class PlacedGroupContent(PlacedContent):
    group: List[PlacedContent] = None

    @classmethod
    def from_items(cls, represents, items: Iterable[PlacedContent], extent: Extent,
                   extra_unused: int) -> PlacedGroupContent:
        placed = list(items)
        error = Error.sum(i.error for i in placed) + Error(0, 0, 0, extra_unused)
        return PlacedGroupContent(represents, extent, Point(0, 0), error, placed)

    def _draw(self, pdf: PDF):
        for p in self.group:
            p.draw(pdf)


@dataclass
class PlacedRunContent(PlacedContent):
    segments: List[TextSegment]  # base text pieces
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        pdf.draw_text(self.segments)


def _debug_draw_rect(pdf, represents, rect):
    if pdf.debug:
        if isinstance(represents, Sheet):
            # Don't draw sheet -- we know where it is
            return
        elif isinstance(represents, Section):
            r, g, b, a = 1, 0.7, 0, 0.15
        elif isinstance(represents, Block):
            r, g, b, a = 0, 0, 1, 0.15
        elif isinstance(represents, Item):
            r, g, b, a = 1, 0, 0, 0.2
        elif isinstance(represents, Run):
            r, g, b, a = 1, 0, 1, 0.2
        else:
            raise ValueError('Unexpected representation: ' + str(represents))
        pdf.saveState()
        pdf.setFillColorRGB(r, g, b, alpha=a)
        pdf.setStrokeColorRGB(r, g, b, alpha=a * 2.5)
        pdf.draw_rect(rect, DrawMethod.BOTH)
        pdf.restoreState()
