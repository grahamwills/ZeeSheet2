from __future__ import annotations

import reprlib
from copy import copy
from dataclasses import dataclass
from typing import List, Optional

import common
import layout.quality
from common import Extent, Point, Rect, Spacing
from common import configured_logger, to_str
from generate.pdf import TextSegment, PDF
from layout.quality import PlacementQuality
from structure import ImageDetail
from structure.style import Style

LOGGER = configured_logger(__name__)


def _f(v) -> str:
    return to_str(v, places=1)


@dataclass
class PlacedContent:
    extent: Extent  # The size we made it
    location: Point  # Where it was placed within the parent
    quality: PlacementQuality  # How good the placement is
    required_width: Optional[float]  # The width we want to be

    def __post_init__(self):
        self.hidden = False

    @property
    def bounds(self) -> Rect:
        return Rect(self.location.x,
                    self.location.x + self.extent.width,
                    self.location.y,
                    self.location.y + self.extent.height)

    def better(self, other:type(PlacedContent)):
        return other is None or self.quality.better(other.quality)

    def _draw(self, pdf: PDF):
        raise NotImplementedError('Must be defined in subclass')

    def __str__(self):
        txt = '<HIDDEN, ' if self.hidden else '<'
        txt += 'bds=' + str(round(self.bounds)) + ", quality=" + str(self.quality)
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
    def from_items(cls, items: List[PlacedContent], quality: PlacementQuality,
                   extent: Extent = None) -> PlacedGroupContent:
        req_wid = max((p.required_width for p in items if p.required_width), default=None)
        if extent is None:
            r = Rect.union(i.bounds for i in items)
            extent = r.extent
        return PlacedGroupContent(extent, Point(0, 0), quality, req_wid, items)


    def _draw(self, pdf: PDF):
        for p in self.group:
            p.draw(pdf)

    def __str__(self):
        base = super().__str__()
        return base[0] + '#items=' + _f(len(self.group)) + ', ss=' + _f(self.sum_squares_unused_space) + ', ' + base[1:]

    def __copy__(self):
        group = [copy(g) for g in self.group]
        return PlacedGroupContent(self.extent, self.location, self.quality, self.required_width,
                                  group, self.sum_squares_unused_space)

    def __getitem__(self, item) -> type(PlacedContent):
        return self.group[item]

    def name(self):
        contents = set(c.__class__.__name__.replace('Placed', '').replace('Content', '') for c in self.group)
        if contents:
            what = '-' + '•'.join(sorted(contents))
        else:
            what = ''
        return f"Group({len(self.group)}){what}"


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
        return PlacedRunContent(self.extent, self.location, self.quality, self.required_width, self.segments, self.style)

    def name(self):
        return ''.join(s.to_text() for s in self.segments)


@dataclass
class PlacedRectContent(PlacedContent):
    style: Style  # Style for this item

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)

    def __copy__(self):
        return PlacedRectContent(self.extent, self.location, self.quality, self.required_width, self.style)

    def name(self):
        return 'Rect' + common.name_of(tuple(self.bounds))


@dataclass
class PlacedImageContent(PlacedContent):
    image: ImageDetail

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_image(self.image.data, self.extent)

    def __copy__(self):
        return PlacedImageContent(self.extent, self.location, self.quality, self.required_width, self.image)

    def name(self):
        return 'Image#' + str(self.image.index)


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
        return PlacedRectContent(bounds.extent, bounds.top_left, layout.quality.for_decoration(bounds), None, base_style)
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
    if mode == 'stretch':
        # Stretch to the bounds
        e = bounds.extent
    elif mode == 'fill' or mode == 'normal' and (width > bounds.width or height > bounds.height):
        # Keep same aspect as we scale
        scale = min(bounds.width / width, bounds.height / height)
        e = Extent(scale * width, scale * height)
    else:
        e = Extent(width, height)

    # Place it relative to the bounds
    dx = bounds.width - e.width
    dy = bounds.height - e.height
    if anchor in {'nw', 'w', 'sw'}:
        x = 0
    elif anchor in {'ne', 'e', 'se'}:
        x = dx
    else:
        x = dx / 2

    if anchor in {'nw', 'n', 'ne'}:
        y = 0
    elif anchor in {'sw', 's', 'se'}:
        y = dy
    else:
        y = dy / 2

    required_width = width if mode == 'normal' else None
    quality = layout.quality.for_image(image, e.width, bounds.width, e.height, bounds.height)
    return PlacedImageContent(e, Point(x + bounds.left, y + bounds.top), quality, required_width, image)


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
