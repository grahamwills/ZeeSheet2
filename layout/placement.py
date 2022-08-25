from typing import List, Optional, NamedTuple

from common.geom import Extent, Point
from generate.pdf import PDF, TextSegment, FontInfo
from layout.content import PlacedGroupContent, PlacedRunContent, PlacedContent, Error
from rst.structure import Run, Item, Block


class SplitResult(NamedTuple):
    """Contains the results of splitting  text for wrapping purposes"""
    fit: Optional[str]
    fit_width: float
    next_line: Optional[str]
    bad_break: bool


def split_for_wrap(text: str,
                   available: float,
                   font: FontInfo,
                   allow_bad_breaks: bool = False) -> SplitResult:
    """
        Splits the text into two parts to facilitate wrapping

        :param text: text to break
        :param available: space available to place into
        :param font: the font being used
        :param allow_bad_breaks: if true, can break anywhere
        :return: the string that fits and the width of that string followed by the remainder of the string,
        and then a flag for a bad break
    """

    width = font.width(text)
    if width <= available:
        # Easy if it all fits!
        return SplitResult(text, width, None, False)

    # Search through in order
    # (might be faster to do a search starting from a fraction (available/width) of the string)

    best = None
    for at in range(1, len(text) - 1):
        if allow_bad_breaks or text[at].isspace():
            head = text[:at]
            w = font.width(head.rstrip())
            if w < available:
                best = head, w
            else:
                break

    if best:
        head = best[0]
        tail = text[len(head):]
        split_good = head[-1].isspace() or tail[0].isspace()
        return SplitResult(head.rstrip(), best[1], tail.lstrip(), not split_good)
    else:
        return SplitResult(None, 0, text, False)


def place_run(run: Run, extent: Extent, pdf: PDF) -> PlacedRunContent:
    placed = _place_run(run, extent, pdf, False)

    if not placed.error.clipped:
        # Fits into the extent requested
        return placed

    # Try with bad breaks
    placed1 = _place_run(run, extent, pdf, True)
    return placed1 if placed1.better(placed) else placed


def _place_run(run: Run, extent: Extent, pdf: PDF, allow_bad_breaks: bool) -> PlacedRunContent:
    segments: List[TextSegment] = []

    x, y, right, bottom = 0, 0, 0, 0
    area_used = 0
    acceptable_breaks, bad_breaks, clipped = 0, 0, 0
    for element in run.children:
        font = element.modify_font(pdf.font)
        text = element.value
        height = font.line_spacing

        while text is not None:
            if y + height > extent.height:
                # Clipped text; just add the size of the clipped area
                clipped += height * font.width(text)
                break

            split = split_for_wrap(text, extent.width - x, font, allow_bad_breaks=allow_bad_breaks)
            if not split.fit and not x and not allow_bad_breaks:
                # Failed to split with whole line available - try again, but allow bad breaks just for this line
                split = split_for_wrap(text, extent.width - x, font, allow_bad_breaks=True)
            if not split.fit and not x:
                # Still failed
                raise RuntimeError('An empty line cannot fit a single character')

            if split.fit:
                # Put it on this line
                segments.append(TextSegment(split.fit, Point(x, y), font))
                x += split.fit_width
                right = max(right, x)
                bottom = max(bottom, y + height)
                area_used += split.fit_width * height

            if split.next_line:
                # Start a new line
                x = 0
                y += height
                if split.bad_break:
                    bad_breaks += 1
                else:
                    acceptable_breaks += 1

            # Continue to process the tail text, if it exists
            text = split.next_line

    bounds = Extent(right, bottom)
    error = Error(
        clipped,
        bad_breaks,
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
    items: List[PlacedContent] = []
    y = 0

    if block.title:
        placed_title = place_run(block.title, extent, pdf)
        y += placed_title.extent.height
        items.append(placed_title)

    # Find out how many columns we have
    ncols = max(len(item.children) for item in block.children)

    # Evenly space everything and assume everything fits


    y_next = 0
    for item in block.children:
        for i, run in enumerate(item.children):
            cell_extent = Extent(extent.width/ncols, extent.height)
            x = i * cell_extent.width
            placed_run = place_run(run, cell_extent, pdf)
            placed_run.location = Point(x, y)
            y_next = max(y_next, placed_run.bounds.bottom)
            items.append(placed_run)
        y = y_next

    outer_bounds = Extent(extent.width, y)

    # TODO: Fix this
    extra_space = 0

    return PlacedGroupContent.from_items(block, items, outer_bounds, extra_space)
