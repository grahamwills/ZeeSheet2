from copy import copy
from functools import lru_cache
from typing import Optional, NamedTuple, Tuple, List

from common import Extent, Point, Spacing, Rect, configured_logger
from generate.pdf import PDF
from layout.content import PlacedGroupContent, PlacedRunContent, PlacedContent, PlacedRectContent, ItemDoesNotExistError
from layout.packing import ColumnPacker
from layout.run_builder import RunBuilder
from structure import Run, Block
from structure.style import Style

# Constant for use when no spacing needed
NO_SPACING = Spacing.balanced(0)

LOGGER = configured_logger(__name__)


class SplitResult(NamedTuple):
    """Contains the results of splitting  text for wrapping purposes"""
    fit: Optional[str]
    fit_width: float
    next_line: Optional[str]
    bad_break: bool


@lru_cache(maxsize=10000)
def place_run(run: Run, extent: Extent, style: Style, pdf: PDF) -> PlacedRunContent:
    bldr = RunBuilder(run, style, extent, pdf)
    placed = bldr.build()

    # Apply alignment
    if style.text.align == 'right':
        placed.offset_content(extent.width - placed.extent.width)
    elif style.text.align == 'center':
        placed.offset_content((extent.width - placed.extent.width) / 2)

    # After alignment, it fills the width. Any unused space is captured in the extent
    placed.extent = Extent(extent.width, placed.extent.height)
    return placed


def make_title(block: Block, inner: Rect, pdf: PDF) -> Tuple[Optional[PlacedContent], Spacing]:
    if not block.title or block.options.title == 'none':
        return None, NO_SPACING

    if block.options.title != 'simple':
        # warnings.warn(f"Border style '{block.options.title}' is not yet supported, treating as 'simple'")
        pass

    title_style = pdf.styles[block.options.title_style]

    title_bounds = title_style.box.inset_within_padding(inner)
    placed = copy(place_run(block.title, title_bounds.extent, title_style, pdf))
    placed.location = title_bounds.top_left

    r1 = title_style.box.inset_within_margin(inner)
    r2 = title_style.box.outset_to_border(placed.bounds)
    plaque_rect = Rect(r1.left, r1.right, r2.top, r2.bottom)
    plaque_rect_to_draw = plaque_rect

    if title_style.box.has_border():
        # Need to reduce the plaque to draw INSIDE the border
        plaque_rect_to_draw = plaque_rect - Spacing.balanced(title_style.box.width / 2)

    plaque = PlacedRectContent(plaque_rect_to_draw.extent, plaque_rect_to_draw.top_left, None, title_style)
    title_extent = plaque_rect.extent + title_style.box.margin
    spacing = Spacing(0, 0, title_extent.height, 0)

    return PlacedGroupContent.from_items([plaque, placed], title_extent), spacing


def locate_title(title: PlacedContent, outer: Rect, content_extent: Extent, pdf: PDF) -> None:
    """ Defines the title location and returns the bounds of everything including the title"""

    # Currently we only do simple -- at the top
    if title:
        title.location = Point(0, 0)


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


def place_block(block: Block, size: Extent, pdf: PDF) -> PlacedContent:
    """ Margins have already been inset when we get into here"""

    main_style = pdf.styles[block.options.style]
    container = Rect(0, size.width, 0, size.height)

    # Inset for just the border; everything lives inside the border
    if main_style.box.has_border():
        outer = container - Spacing.balanced(main_style.box.width)
    else:
        outer = container

    # Create the title and insets to allow room for it
    title, title_spacing = make_title(block, outer, pdf)

    if not block.children:
        if not title:
            raise RuntimeError('Need either a title or content in a block')
        else:
            return title

    # Reduce space for the items to account for the title.
    # Inset for padding and border
    item_bounds = outer - title_spacing

    placed_children = place_block_children(block, item_bounds, pdf)
    locate_title(title, outer, placed_children.bounds, pdf)

    # Frame everything
    total_height = placed_children.bounds.bottom
    if title:
        total_height = max(total_height, title.bounds.bottom)
    if main_style.box.has_border():
        total_height += main_style.box.width
    frame_bounds = Rect(0, size.width, 0, total_height)
    frame = make_frame(frame_bounds, main_style)

    # Make the valid items
    items = [i for i in (frame, placed_children, title) if i]
    if len(items) == 1:
        return items[0]

    block_extent = Extent(size.width, total_height)
    return PlacedGroupContent.from_items(items, extent=block_extent)


class BlockColumnPacker(ColumnPacker):
    def __init__(self, bounds: Rect, block: Block, pdf: PDF):
        column_count = max(len(item.children) for item in block.children)
        self.items = block.children
        self.pdf = pdf
        self.content_style = pdf.styles[block.options.style]
        super().__init__(bounds, len(block.children), column_count, granularity=10)

    def place_table(self, width_allocations: List[float] = None):
        table = super().place_table(width_allocations)
        return copy(table)

    def margins_of_item(self, idx) -> Spacing:
        # All block items share common margins
        return self.content_style.box.padding

    def place_item(self, idx: Tuple[int, int], extent: Extent) -> PlacedContent:
        items = self.items[idx[0]]
        if idx[1] < len(items.children):
            return place_run(items[idx[1]], extent, self.content_style, self.pdf)
        else:
            raise ItemDoesNotExistError()


@lru_cache
def place_block_children(block: Block, item_bounds: Rect, pdf) -> Optional[PlacedGroupContent]:
    if block.children:
        packer = BlockColumnPacker(item_bounds, block, pdf)
        return packer.place_table()
    else:
        return None
