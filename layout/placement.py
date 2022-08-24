from typing import List, Tuple, Optional

from common.geom import Extent, Point
from generate.pdf import PDF, TextSegment, FontInfo
from layout.content import PlacedGroupContent, PlacedRunContent, PlacedContent, Error
from rst.structure import Run, Item, Block


def split_for_wrap(text: str, available: float, font: FontInfo) -> Tuple[Optional[str], float, Optional[str]]:
    """
        Splits the text into two parts to facilitate wrapping

        :param text: text to break
        :param available: space available to place into
        :param font: the font being used
        :return: the string that fits and the width of that string followed by the remainder of the string
    """

    width = font.width(text)
    if width <= available:
        # Easy if it all fits!
        return text, width, None

    # Search through in order
    # (might be faster to do a search starting from a fraction (available/width) of the string)

    best, best_w = None, 0
    for at in range(1, len(text) - 1):
        if text[at:at + 1].isspace():
            head = text[:at].strip()
            w = font.width(head)
            if w < available:
                best, best_w = head, w
            else:
                break

    if best:
        remainder = text[len(best):].lstrip()
        return best, best_w, remainder
    else:
        return None, 0, text


def place_run(run: Run, extent: Extent, pdf: PDF) -> PlacedRunContent:
    segments: List[TextSegment] = []

    x, y, right, bottom = 0, 0, 0, 0
    area_used = 0
    acceptable_breaks = 0
    for element in run.children:
        font = pdf.font
        text = element.value
        height = font.line_spacing
        while text is not None:
            head, width, tail = split_for_wrap(text, extent.width - x, font)
            if head:
                # Put it on this line
                segments.append(TextSegment(head, Point(x, y)))
                x += width
                right = max(right, x)
                bottom = max(bottom, y + height)
                area_used += width * height
            else:
                if x == 0:
                    raise RuntimeError('An empty line cannot fit this text')

            if tail:
                # Start a new line
                x = 0
                y += height
                acceptable_breaks += 1

            # Continue to process the tail text, if it exists
            text = tail

    bounds = Extent(right, bottom)
    error = Error(
        0,
        0,
        acceptable_breaks,
        bounds.area - area_used  # Unused space in square pixels
    )
    return PlacedRunContent(run, bounds, Point(0, 0), error, segments)


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

    return PlacedGroupContent.from_items(item, items, outer_bounds, extra_space)


def place_block(block: Block, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    ITEM_SPACING = 0
    items: List[PlacedContent] = []
    x, y = 0, 0

    if block.title:
        placed_title = place_run(block.title, extent, pdf)
        y += placed_title.extent.height
        items.append(placed_title)

        # Extra spacing for the title to be fixed later
        y += ITEM_SPACING + ITEM_SPACING

    for item in block.children:
        placed_item = place_item(item, extent, pdf)
        placed_item.location = Point(x, y)
        y += placed_item.extent.height + ITEM_SPACING
        items.append(placed_item)

    y -= ITEM_SPACING

    outer_bounds = Extent(extent.width, y)
    extra_space = 0

    return PlacedGroupContent.from_items(block, items, outer_bounds, extra_space)
