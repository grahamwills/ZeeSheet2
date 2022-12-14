from __future__ import annotations

import abc
import reprlib
from copy import copy
from dataclasses import dataclass
from typing import List, Optional, Any

from reportlab.graphics.shapes import Path

import common
import layout.quality
from common import Extent, Point, Rect, Spacing
from common import configured_logger, to_str
from drawing import PDF, coords_to_path
from drawing.pdf import Segment, TextFieldSegment
from layout.quality import PlacementQuality
from structure import CommonOptions, to_color
from structure import ImageDetail
from structure import Style, BoxStyle

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

    def drawn_bounds(self) -> Rect:
        """ The bounds of objects actually drawn, as opposed to theoretical bounds """
        raise NotImplementedError('Must be defined in subclass')

    def as_path(self) -> Path:
        raise NotImplementedError('Must be defined in subclass')

    def contains_expandable(self) -> bool:
        """ True if this content contains an expandable text field"""
        raise NotImplementedError('Must be defined in subclass')

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
            pdf.setFillColor(to_color(color))
            pdf.setFillAlpha(fill_a)
            pdf.rect(0, 0, self.extent.width, self.extent.height, fill=1, stroke=0)
            pdf.restoreState()
            pdf.saveState()

        self._draw(pdf)

        if pdf.debug and self.DEBUG_STYLE:
            pdf.restoreState()
            color, stroke_a, fill_a, width, dash = self.DEBUG_STYLE
            pdf.setStrokeColor(to_color(color))
            pdf.setStrokeAlpha(stroke_a)
            pdf.setLineWidth(width)
            if dash:
                pdf.setDash(dash)
            pdf.rect(0, 0, self.extent.width, self.extent.height, fill=0, stroke=1)

        pdf.restoreState()

    def _debug_draw(self, pdf):
        if pdf.debug:
            color, stroke_a, fill_a, width, dash = self.DEBUG_STYLE
            c = to_color(color)
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
    clip_item: PlacedContent = None

    def __init__(self, items: List[PlacedContent], extent: Extent, quality: PlacementQuality,
                 location: Point = ZERO, clip_item: PlacedContent = None):
        super().__init__(extent, quality, location)
        self.items = items
        self.clip_item = clip_item

    def drawn_bounds(self) -> Rect:
        return Rect.union(p.drawn_bounds() for p in self.items) + self.location

    def as_path(self) -> Path:
        raise NotImplementedError('Grouped content does not provide a path')

    def children(self) -> List[PlacedContent]:
        return self.items

    def contains_expandable(self) -> bool:
        return any(s.contains_expandable() for s in self.items)

    @classmethod
    def from_items(cls, items: List[PlacedContent], quality: PlacementQuality,
                   extent: Extent = None) -> PlacedGroupContent:
        if extent is None:
            r = Rect.union(i.bounds for i in items)
            extent = r.extent
        return PlacedGroupContent(items, extent, quality, ZERO)

    # noinspection PyUnboundLocalVariable,PyUnresolvedReferences
    def _draw(self, pdf: PDF):
        clip = self.clip_item
        if clip:
            pdf.saveState()
            pdf.clipPath(clip.as_path(), 0, 0)
            box: BoxStyle = clip.style.box
            original_border = box.border_color
            box.border_color = 'none'

        for p in self.items:
            p.draw(pdf)
        if clip:
            pdf.restoreState()
            box.border_color = original_border
            original_fill = box.color
            box.color = 'none'
            clip.draw(pdf)
            box.color = original_fill

    def __str__(self):
        base = super().__str__()
        return base[0] + '#items=' + to_str(len(self.items), places=1) + ', ' + base[1:]

    def __copy__(self):
        items = [copy(g) for g in self.items]
        return PlacedGroupContent(items, self.extent, self.quality, self.location, self.clip_item)

    def __getitem__(self, item) -> type(PlacedContent):
        return self.items[item]

    def name(self):
        contents = set(c.__class__.__name__.replace('Placed', '').replace('Content', '') for c in self.items)
        if contents:
            what = '-' + '???'.join(sorted(contents))
        else:
            what = ''
        return f"Group({len(self.items)}){what}"


@dataclass
class PlacedRunContent(PlacedContent):
    def as_path(self) -> Path:
        raise NotImplementedError('Run content does not provide a path')

    DEBUG_STYLE = ('#590696', 0.75, 0.1, 1, None)

    segments: List[Segment]  # base text pieces
    style: Style  # Style for this item

    def __init__(self, segments: List[Segment], style: Style, extent: Extent, quality: PlacementQuality,
                 location: Point = ZERO):
        super().__init__(extent, quality, location)
        self.segments = segments
        self.style = style

    def _draw(self, pdf: PDF):
        pdf.draw_text(self.style, self.segments)

    def contains_expandable(self) -> bool:
        return any(isinstance(s, TextFieldSegment) and s.expands for s in self.segments)

    def drawn_bounds(self) -> Rect:
        if not self.segments:
            return Rect(self.location.x, self.location.x, self.location.y, self.location.y)
        left = min(s.x for s in self.segments)
        right = max(s.x + s.width for s in self.segments)
        return Rect(left + self.location.x, right + self.location.x,
                    self.location.y, self.location.y + self.extent.height)

    def as_path(self) -> Path:
        raise NotImplementedError('Grouped content does not provide a path')

    def offset_content(self, dx: float):
        for s in self.segments:
            s.x += dx

    def __str__(self):
        base = super().__str__()
        txt = ''.join(s.to_text() for s in self.segments)
        return base[0] + reprlib.repr(txt) + ', ' + base[1:]

    def __copy__(self):
        segments = [copy(s) for s in self.segments]
        return PlacedRunContent(segments, self.style, self.extent, self.quality, self.location)

    def name(self):
        return ''.join(s.to_text() for s in self.segments)


@dataclass
class PlacedRectContent(PlacedContent):
    DEBUG_STYLE = None

    style: Style  # Style for this item
    _asPath: Path = None

    def __init__(self, bounds: Rect, style: Style, quality: PlacementQuality):
        super().__init__(bounds.extent, quality, bounds.top_left)
        self.style = style

    def as_path(self) -> Path:
        if not self._asPath:
            effect = self.style.get_effect()
            coords = self.bounds.path_coords()
            self._asPath = coords_to_path(coords, effect, hash(self.bounds))
        return self._asPath

    def contains_expandable(self) -> bool:
        return False

    def drawn_bounds(self) -> Rect:
        return self.bounds

    def _draw(self, pdf: PDF):
        effect = self.style.get_effect()
        if effect.needs_path_conversion:
            pdf.draw_path(self.as_path(), self.style)
        else:
            pdf.draw_rect(Rect(0, self.extent.width, 0, self.extent.height), self.style)

    def __copy__(self):
        return PlacedRectContent(self.bounds, self.style, self.quality)

    def name(self):
        return 'Rect' + common.name_of(tuple(self.bounds))


@dataclass
class PlacedPathContent(PlacedContent):
    DEBUG_STYLE = None

    coords: list[tuple]
    style: Style  # Style for this item
    _asPath: Path = None

    def __init__(self, coords: list[tuple[float, ...]], bounds: Rect, style: Style, quality: PlacementQuality):
        super().__init__(bounds.extent, quality, bounds.top_left)
        self.coords = coords
        self.style = style

    def as_path(self) -> Path:
        if not self._asPath:
            effect = self.style.get_effect()
            self._asPath = coords_to_path(self.coords, effect, hash(self.bounds))
        return self._asPath

    def contains_expandable(self) -> bool:
        return False

    def _draw(self, pdf: PDF):
        pdf.draw_path(self.as_path(), self.style)

    def drawn_bounds(self) -> Rect:
        l, t, r, b = self.as_path().getBounds()
        return Rect(l, r, t, b) + self.location

    def __copy__(self):
        return PlacedPathContent(self.coords, self.bounds, self.style, self.quality)

    def name(self):
        return 'Rect' + common.name_of(tuple(self.bounds))


@dataclass
class PlacedImageContent(PlacedContent):
    DEBUG_STYLE = ('#FBCB0A', 0.75, 0, 3, (1, 10))
    image: ImageDetail
    desired: Extent
    mode: str
    anchor: str
    brightness: float
    contrast: float

    def as_path(self) -> Path:
        raise NotImplementedError('Image content does not provide a path')

    def __init__(self, image: ImageDetail, desired: Extent, mode: str, anchor: str, bounds: Rect,
                 brightness: float, contrast: float, quality: PlacementQuality = None):
        super().__init__(bounds.extent, quality, bounds.top_left)
        self.desired = desired
        self.image = image
        self.mode = mode
        self.anchor = anchor
        self.contrast = contrast
        self.brightness = brightness

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

    def contains_expandable(self) -> bool:
        # TODO: Should this be true for images that can expand?
        return False

    def drawn_bounds(self) -> Rect:
        return self.image_bounds() + self.location

    def shrink_to_fit(self, bottom: float) -> float:
        dy = self.bounds.bottom - bottom
        self.extent = self.extent - Extent(0, dy)
        self.quality = layout.quality.for_image(self.mode, self.desired, self.image_bounds(), self.bounds)
        return dy

    def _draw(self, pdf: PDF):
        pdf.draw_image(self.image.data, self.image_bounds(), self.brightness, self.contrast)

    def __copy__(self):
        return PlacedImageContent(self.image, self.desired, self.mode, self.anchor, self.bounds,
                                  self.brightness, self.contrast, self.quality)

    def name(self):
        return 'Image#' + str(self.image.index)


def make_frame(bounds: Rect, style: Style,
               options: CommonOptions, pdf: PDF) -> Optional[PlacedContent]:
    box = make_frame_box(bounds, style)
    if options.image:
        im = pdf.get_image(options.image)
        if im:
            image = make_image(im, bounds, options.image_mode, options.image_width,
                               options.image_height, options.image_anchor,
                               options.image_brightness, options.image_contrast,
                               force_to_top=False)
            if box:
                return PlacedGroupContent.from_items([box, image], layout.quality.for_decoration())
            else:
                return image

    return box


def make_frame_box(bounds: Rect, style: Style) -> Optional[PlacedRectContent]:
    s = style.box
    has_background = s.color != 'none' and s.opacity > 0
    has_border = s.border_color != 'none' and s.border_opacity > 0 and s.width > 0
    if has_border or has_background:
        if s.has_border():
            # Inset because the stroke is drawn centered around the box, and we want it drawn just within
            bounds = bounds - Spacing.balanced(s.width / 2)
        return PlacedRectContent(bounds, style, layout.quality.for_decoration())
    else:
        return None


def make_image(image: ImageDetail, bounds: Rect, mode: str, width: float, height: float,
               anchor: str, brightness: float, contrast: float, force_to_top: bool) -> PlacedImageContent:
    # Ensure width and height are defined
    aspect = image.height / image.width
    if not width and not height:
        width = image.width
        height = image.height
    elif not height:
        height = width * aspect
    elif not width:
        width = height / aspect

    content = PlacedImageContent(image, Extent(width, height), mode, anchor, bounds, brightness, contrast)
    image_bounds = content.image_bounds()
    content.quality = layout.quality.for_image(mode, Extent(width, height), image_bounds, bounds)
    if force_to_top:
        # We do this when it is the only content of a block as we don't want that extra space on top
        content.location = Point(content.location.x, bounds.top)
        content.extent = image_bounds.extent
    else:
        content.extent = bounds.extent
    return content


class ExtentTooSmallError(Exception):
    """ The space is too small to fit anything """

    def __init__(self, target: Any, info: str) -> None:
        super().__init__(f"Extent too small to fit {common.name_of(target)}: {info}")
        self.target = target
        self.info = info
