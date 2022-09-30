from __future__ import annotations

import abc
import reprlib
from copy import copy
from dataclasses import dataclass
from typing import List, Optional

from reportlab.lib.colors import toColor

import common
import layout.quality
from common import Extent, Point, Rect, Spacing
from common import configured_logger, to_str
from generate.pdf import TextSegment, PDF
from layout.quality import PlacementQuality
from structure import ImageDetail
from structure.style import Style

LOGGER = configured_logger(__name__)

ZERO = Point(0, 0)


class PlacedContent(abc.ABC):
    DEBUG_STYLE = ('#000000', 0.5, 0.1, 0.25, None)

    extent: Extent  # The size we made it
    quality: PlacementQuality  # How good the placement is
    location: Point  # Where it was placed within the parent
    hidden: bool  # Do we want to draw this?

    def __init__(self, extent: Extent, quality: PlacementQuality, location):
        self.quality = quality
        self.location = location
        self.extent = extent
        self.hidden = False

    def children(self) -> List[PlacedContent]:
        raise AttributeError(self.__class__.__name__ + ' does not have children')

    def child(self, i: int) -> PlacedContent:
        return self.children()[i]

    @property
    def bounds(self) -> Rect:
        return Rect(self.location.x,
                    self.location.x + self.extent.width,
                    self.location.y,
                    self.location.y + self.extent.height)

    def better(self, other: type(PlacedContent)):
        return other is None or self.quality.better(other.quality)

    def _draw(self, pdf: PDF):
        raise NotImplementedError('Must be defined in subclass')

    def __str__(self):
        txt = '<HIDDEN, ' if self.hidden else '<'
        txt += 'bds=' + str(round(self.bounds)) + ", quality=" + str(self.quality)
        return txt + '>'

    def draw(self, pdf: PDF):
        if self.hidden:
            return
        pdf.saveState()
        if self.location:
            pdf.translate(self.location.x, self.location.y)

        if pdf.debug and self.DEBUG_STYLE:
            color, stroke_a, fill_a, width, dash = self.DEBUG_STYLE
            pdf.saveState()
            pdf.setFillColor(toColor(color))
            pdf.setFillAlpha(fill_a)
            pdf.rect(0, 0, self.extent.width, self.extent.height, fill=1, stroke=0)
            pdf.restoreState()
            pdf.saveState()

        self._draw(pdf)

        if pdf.debug and self.DEBUG_STYLE:
            pdf.restoreState()
            color, stroke_a, fill_a, width, dash = self.DEBUG_STYLE
            pdf.setStrokeColor(toColor(color))
            pdf.setStrokeAlpha(stroke_a)
            pdf.setLineWidth(width)
            if dash:
                pdf.setDash(dash)
            pdf.rect(0, 0, self.extent.width, self.extent.height, fill=0, stroke=1)

        pdf.restoreState()

    def _debug_draw(self, pdf):
        if pdf.debug:
            color, stroke_a, fill_a, width, dash = self.DEBUG_STYLE
            c = toColor(color)
            pdf.saveState()
            pdf.setFillColor(c)
            pdf.setStrokeColor(c)
            pdf.setFillAlpha(fill_a)
            pdf.setStrokeAlpha(stroke_a)
            pdf.setLineWidth(width)
            if dash:
                pdf.setDash(dash)
            pdf.rect(0, 0, self.extent.width, self.extent.height, fill=1, stroke=1)
            pdf.restoreState()


class PlacedGroupContent(PlacedContent):
    DEBUG_STYLE = ('#C70A80', 0.25, 0.1, 3, None)

    items: List[PlacedContent] = None

    def __init__(self, items: List[PlacedContent], extent: Extent, quality: PlacementQuality,
                 location: Point = ZERO):
        super().__init__(extent, quality, location)
        self.items = items

    def children(self) -> List[PlacedContent]:
        return self.items

    @classmethod
    def from_items(cls, items: List[PlacedContent], quality: PlacementQuality,
                   extent: Extent = None) -> PlacedGroupContent:
        if extent is None:
            r = Rect.union(i.bounds for i in items)
            extent = r.extent
        return PlacedGroupContent(items, extent, quality, ZERO)

    def _draw(self, pdf: PDF):
        for p in self.items:
            p.draw(pdf)

    def __str__(self):
        base = super().__str__()
        return base[0] + '#items=' + to_str(len(self.items), places=1) + ', ' + base[1:]

    def __copy__(self):
        items = [copy(g) for g in self.items]
        return PlacedGroupContent(items, self.extent, self.quality, self.location)

    def __getitem__(self, item) -> type(PlacedContent):
        return self.items[item]

    def name(self):
        contents = set(c.__class__.__name__.replace('Placed', '').replace('Content', '') for c in self.items)
        if contents:
            what = '-' + '•'.join(sorted(contents))
        else:
            what = ''
        return f"Group({len(self.items)}){what}"


@dataclass
class PlacedRunContent(PlacedContent):
    DEBUG_STYLE = ('#590696', 0.75, 0.1, 1, None)

    segments: List[TextSegment]  # base text pieces
    style: Style  # Style for this item

    def __init__(self, segments: List[TextSegment], style: Style, extent: Extent, quality: PlacementQuality,
                 location: Point = ZERO):
        super().__init__(extent, quality, location)
        self.segments = segments
        self.style = style

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
        return PlacedRunContent(self.segments, self.style, self.extent, self.quality, self.location)

    def name(self):
        return ''.join(s.to_text() for s in self.segments)


@dataclass
class PlacedRectContent(PlacedContent):
    DEBUG_STYLE = None

    style: Style  # Style for this item

    def __init__(self, bounds: Rect, style: Style, quality: PlacementQuality):
        super().__init__(bounds.extent, quality, bounds.top_left)
        self.style = style

    def _draw(self, pdf: PDF):
        # We have already been offset by the top left
        pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)

    def __copy__(self):
        return PlacedRectContent(self.bounds, self.style, self.quality)

    def name(self):
        return 'Rect' + common.name_of(tuple(self.bounds))


@dataclass
class PlacedImageContent(PlacedContent):
    DEBUG_STYLE = ('#FBCB0A', 0.75, 0, 3, (1, 10))
    image: ImageDetail
    desired: Extent
    mode: str
    anchor: str

    def __init__(self, image: ImageDetail, desired: Extent, mode: str, anchor: str, bounds: Rect,
                 quality: PlacementQuality = None):
        super().__init__(bounds.extent, quality, bounds.top_left)
        self.desired = desired
        self.image = image
        self.mode = mode
        self.anchor = anchor

    def image_bounds(self):
        mode = self.mode
        anchor = self.anchor
        bounds = self.bounds
        width = self.desired.width
        height = self.desired.height

        if mode == 'stretch':
            width = bounds.width
            height = bounds.height
        elif mode == 'fill':
            # Scale to fill either width or height
            scale = min(bounds.width / width, bounds.height / height)
            width *= scale
            height *= scale
        else:
            # Only shrink if we have to
            if width > bounds.width or height > bounds.height:
                scale = min(bounds.width / width, bounds.height / height)
                width *= scale
                height *= scale

        # Place it relative to the bounds
        dx = bounds.width - width
        dy = bounds.height - height
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

        return Rect(x, x + width, y, y + height)

    def shrink_to_fit(self, bottom:float) -> float:
        dy = self.bounds.bottom - bottom
        self.extent = self.extent - Extent(0, dy)
        self.quality = layout.quality.for_image(self.quality.target, self.mode, self.desired, self.image_bounds(), self.bounds)
        return dy


    def _draw(self, pdf: PDF):
        pdf.draw_image(self.image.data, self.image_bounds())

    def __copy__(self):
        return PlacedImageContent(self.image, self.desired, self.mode, self.anchor, self.bounds, self.quality)

    def name(self):
        return 'Image#' + str(self.image.index)


def make_frame(bounds: Rect, style: Style) -> Optional[PlacedRectContent]:
    s = style.box
    has_background = s.color != 'none' and s.opacity > 0
    has_border = s.border_color != 'none' and s.border_opacity > 0 and s.width > 0
    if has_border or has_background:
        if s.has_border():
            # Inset because the stroke is drawn centered around the box and we want it drawn just within
            bounds = bounds - Spacing.balanced(s.width / 2)
        return PlacedRectContent(bounds, style, layout.quality.for_decoration(bounds))
    else:
        return None


def make_image(image: ImageDetail, bounds: Rect, mode: str, width: float, height: float,
               anchor: str) -> PlacedImageContent:
    # Ensure width and height are defined
    aspect = image.height / image.width
    if not width and not height:
        width = image.width
        height = image.height
    elif not height:
        height = width * aspect
    elif not width:
        width = height / aspect

    content = PlacedImageContent(image, Extent(width, height), mode, anchor, bounds)
    image_bounds = content.image_bounds()
    content.quality = layout.quality.for_image(image, mode, Extent(width, height), image_bounds, bounds)
    content.extent = image_bounds.extent
    content.location = Point(content.location.x, 0)
    LOGGER.error(f"{bounds} -> {image_bounds}, err={content.quality}")
    return content


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
