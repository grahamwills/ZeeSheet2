from __future__ import annotations

import reprlib
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Iterable

from PIL.Image import Image

from common import Extent, Point, Rect, Spacing
from common import configured_logger, to_str
from generate.pdf import TextSegment, PDF
from structure import ImageDetail
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

    def __post_init__(self):
        self.hidden = False
        self.required_width = None

    @property
    def bounds(self) -> Rect:
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
        txt = '<HIDDEN, ' if self.hidden else '<'
        txt += 'bds=' + str(round(self.bounds)) + ", err=" + str(self.error)
        if self.required_width is not None:
            txt += ', req_wid=' + _f(self.required_width)
        return txt + '>'

    def draw(self, pdf: PDF):
        if self.hidden:
            return
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

        # If we placed more children we are DEFINITELY better
        diff = len(self.group) - len(other.group)
        if diff != 0:
            return len(self.group) > len(other.group)

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

    def __getitem__(self, item) -> type(PlacedContent):
        return self.group[item]


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

    def __str__(self):
        base = super().__str__()
        txt = ''.join(s.to_text() for s in self.segments)
        return base[0] + reprlib.repr(txt) + ', ' + base[1:]

    def __copy__(self):
        content = PlacedRunContent(self.extent, self.location, self.error, self.segments, self.style)
        content.required_width = self.required_width
        return content


@dataclass
class PlacedRectContent(PlacedContent):
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)

    def __copy__(self):
        return PlacedRectContent(self.extent, self.location, self.error, self.style)


@dataclass
class PlacedImageContent(PlacedContent):
    image: Image

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_image(self.image, self.extent)

    def __copy__(self):
        return PlacedImageContent(self.extent, self.location, self.error, self.image)


def _debug_draw_rect(pdf, rect):
    if pdf.debug:
        r, g, b, a = 1, 0, 1, 0.2
        pdf.saveState()
        pdf.setFillColorRGB(r, g, b, alpha=a)
        pdf.setStrokeColorRGB(r, g, b, alpha=a * 2.5)
        pdf._draw_rect(rect, 1, 1)
        pdf.restoreState()


def make_frame(bounds: Rect, base_style: Style) -> Optional[PlacedRectContent]:
    style = base_style.box
    has_background = style.color != 'none' and style.opacity > 0
    has_border = style.border_color != 'none' and style.border_opacity > 0 and style.width > 0
    if has_border or has_background:
        if style.has_border():
            # Inset because the stroke is drawn centered around the box and we want it drawn just within
            bounds = bounds - Spacing.balanced(style.width / 2)
        return PlacedRectContent(bounds.extent, bounds.top_left, None, base_style)
    else:
        return None


def make_image(image: ImageDetail, bounds: Rect, mode: str, width: float, height: float,
               anchor: str) -> PlacedImageContent:
    aspect = image.height / image.width
    if not width and not height:
        width = image.width
        height = image.height
    elif not height:
        height = width * aspect
    elif not width:
        width = height / aspect

    # Size the image (and keep track of scaling down 'error')
    shrinkage_error = 0
    if mode == 'stretch':
        # Stretch to the bounds
        e = bounds.extent
    elif mode == 'fill' or mode == 'normal' and (width > bounds.width or height > bounds.height):
        # Keep same aspect as we scale
        scale = min(bounds.width / width, bounds.height / height)
        if mode == 'normal':
            shrinkage_error = 1 / scale - 1
        e = Extent(scale * width, scale * height)
    else:
        e = Extent(width, height)

    # Place it relative to the bounds
    dx = bounds.width - e.width
    dy = bounds.height - e.height
    if mode in {'nw', 'w', 'sw'}:
        x = 0
    elif mode in {'ne', 'e', 'se'}:
        x = dx
    else:
        x = dx / 2

    if mode in {'nw', 'n', 'ne'}:
        y = 0
    elif mode in {'sw', 's', 'se'}:
        y = dy
    else:
        y = dy / 2

    return PlacedImageContent(e, Point(x + bounds.left, y + bounds.top),
                              PlacementError(0, shrinkage_error, 0), image.data)


class ExtentTooSmallError(RuntimeError):
    """ The space is too small to fit anything """

    def __init__(self, *args: object) -> None:
        super().__init__(*args)


class ItemDoesNotExistError(RuntimeError):
    """ The item requested to be placed does not exist"""
    pass


class ErrorLimitExceededError(RuntimeError):
    """ The accumulated error has exceeded the maximum allowed"""
    pass
