import warnings
from typing import Optional, NamedTuple, Tuple

from common import Extent, Point, Spacing
from generate.fonts import Font
from generate.pdf import PDF, TextSegment, CheckboxSegment
from layout.content import PlacedGroupContent, PlacedRunContent, Error
from structure import Run, Block
from structure.style import Style

# Constant for use when no spacing needed
_NO_SPACING = Spacing.balanced(0)


class SplitResult(NamedTuple):
    """Contains the results of splitting  text for wrapping purposes"""
    fit: Optional[str]
    fit_width: float
    next_line: Optional[str]
    bad_break: bool


def split_for_wrap(text: str,
                   available: float,
                   font: Font,
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


def place_run(run: Run, extent: Extent, style: Style, pdf: PDF) -> PlacedRunContent:
    placed = _place_run(run, extent, style, pdf, False)

    # If it is not clipped, it is good enough
    if not placed.error.clipped:
        return placed

    # Try with bad breaks
    placed1 = _place_run(run, extent, style, pdf, True)
    return placed1 if placed1.better(placed) else placed


def _place_run(run: Run, extent: Extent, style: Style, pdf: PDF, allow_bad_breaks: bool) -> PlacedRunContent:
    segments = []

    x, y, right, bottom = 0, 0, 0, 0
    area_used = 0
    acceptable_breaks, bad_breaks, clipped = 0, 0, 0
    base_font = pdf.get_font(style)
    for element in run.children:
        font = base_font.change_face(element.modifier == 'strong', element.modifier == 'emphasis')

        text = element.value

        height = font.line_spacing

        # Handle checkbox
        if element.modifier == 'checkbox':
            width = (font.ascent + font.descent) * 1.1  # Add a little spacing (as a small percentage of the box size)
            if y + height > extent.height:
                # Off the bottom -- cannot be placed
                can_be_placed = False
            elif x + width > extent.width:
                # Off the right edge - try to place it on the next line
                x = 0
                y += height
                can_be_placed = (height <= extent.height and width <= extent.width)
            else:
                can_be_placed = True

            if can_be_placed:
                segments.append(CheckboxSegment(text == 'X', Point(x, y), font))
                x += width
            else:
                clipped += width * height * 10
            text = None  # Don't handle this as text in the next block

        # Handle cases of actual text, wrapping if necessary
        while text is not None and text != '':
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
    return PlacedRunContent(run, bounds, Point(0, 0), error, segments, style)


def define_title(block: Block, extent: Extent, pdf: PDF) -> Tuple[Spacing, Optional[PlacedRunContent]]:
    if not block.title or block.options.title == 'none':
        return _NO_SPACING, None

    if block.options.title != 'simple':
        warnings.warn(f"Border style '{block.options.title}' is not yet supported, treating as 'simple'")

    title_style = pdf.styles[block.options.title_style]
    title_spacing = title_style.box.margin
    title_extent = Extent(extent.width - title_spacing.horizontal, extent.height - title_spacing.vertical)
    placed = place_run(block.title, title_extent, title_style, pdf)
    spacing = Spacing(top=placed.extent.height + title_spacing.vertical, left=0, right=0, bottom=0)
    return spacing, placed


def locate_title(title: PlacedRunContent, block: Block, content_extent: Extent, pdf: PDF) -> Extent:
    """ Defines the title location and returns the bounds of everything including the title"""
    if title is None:
        return content_extent

    # Handle as if simple - it's at the top
    margin = pdf.styles[block.options.title_style].box.margin
    title.location = Point(margin.left, margin.top)
    return content_extent


def place_block(block: Block, extent: Extent, pdf: PDF) -> PlacedGroupContent:
    title_spacing, title = define_title(block, extent, pdf)
    if title:
        items = [title]
    else:
        items = []

    # Reduce space to account for the title
    inner = Extent(extent.width - title_spacing.horizontal, extent.height - title_spacing.vertical)
    left = title_spacing.left
    y = title_spacing.top

    if block.children:
        content_style = pdf.styles[block.options.style]

        # Find out how many columns we have
        ncols = max(len(item.children) for item in block.children)

        # Evenly space everything and assume everything fits
        last_item_bottom = y
        for item in block.children:
            for i, run in enumerate(item.children):
                cell_extent = Extent(inner.width / ncols, inner.height)
                x = left + i * cell_extent.width
                placed_run = place_run(run, cell_extent, content_style, pdf)
                placed_run.location = Point(x, y)
                last_item_bottom = max(last_item_bottom, placed_run.bounds.bottom)
                items.append(placed_run)
            y = last_item_bottom

    content_extent = Extent(inner.width, y)
    outer_extent = locate_title(title, block, content_extent, pdf)

    # TODO: Fix this
    extra_space = 0

    return PlacedGroupContent.from_items(block, items, outer_extent, extra_space)
