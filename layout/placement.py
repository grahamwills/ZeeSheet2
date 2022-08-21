from typing import List

from common.geom import Extent, Point
from generate.pdf import PDF, TextSegment
from layout.content import PlacedGroupContent, PlacedElementContent, Error, PlacedContent
from rst.structure import Run, Item, Block


def place_run(run: Run, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    items: List[PlacedElementContent] = []

    # No attempt to split wrapping
    # ignores text modifiers
    # One item per line

    x, y = 0, 0
    for element in run.children:
        font = pdf.font
        text = element.value
        width = font.width(text)
        extent = Extent(width, font.line_spacing)
        error = Error(0, 0, 0)
        split = None
        location = Point(x, y)
        segment = TextSegment(text, location)
        item = PlacedElementContent(element, extent, location, error, split, segment)
        y += font.line_spacing
        items.append(item)

    outer_bounds = Extent(extent.width, y)
    extra_space = 0

    return PlacedGroupContent.from_items(items, outer_bounds, extra_space)


def place_item(item: Item, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    items: List[PlacedContent] = []

    x, y = 0, 0
    for run in item.children:
        placed_run = place_run(run, extent, pdf)
        placed_run.location = Point(x, y)
        y += placed_run.extent.height
        items.append(placed_run)

    outer_bounds = Extent(extent.width, y)
    extra_space = 0

    return PlacedGroupContent.from_items(items, outer_bounds, extra_space)


def place_block(block: Block, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    ITEM_SPACING = 4
    items: List[PlacedContent] = []
    x, y = 0, 0

    if block.title:
        placed_title = place_run(block.title, extent, pdf)
        y += placed_title.extent.height
        items.append(placed_title)

        # Extr spacing for the title to be fixed later
        y += ITEM_SPACING + ITEM_SPACING

    for item in block.children:
        placed_item = place_item(item, extent, pdf)
        placed_item.location = Point(x, y)
        y += placed_item.extent.height + ITEM_SPACING

    y -= ITEM_SPACING

    outer_bounds = Extent(extent.width, y)
    extra_space = 0

    return PlacedGroupContent.from_items(items, outer_bounds, extra_space)
