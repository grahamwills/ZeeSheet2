from typing import Optional, NamedTuple, Tuple

from common import Extent, Point, Spacing, Rect
from generate.fonts import Font
from generate.pdf import PDF, TextSegment, CheckboxSegment
from layout.content import PlacedGroupContent, PlacedRunContent, Error, PlacedContent, PlacedRectContent
from layout.packing import ColumnWidthChooser
from structure import Run, Block
from structure.style import Style

# Constant for use when no spacing needed
NO_SPACING = Spacing.balanced(0)
NO_ERROR = Error(0, 0, 0, 0)


class PlacementError(RuntimeError):
    pass


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
                raise PlacementError('An empty line cannot fit a single character')

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
    return PlacedRunContent(bounds, Point(0, 0), error, segments, style)


def make_title(block: Block, inner: Rect, pdf: PDF) -> Tuple[Optional[PlacedContent], Spacing]:
    # Margin has not been accounted for

    if not block.title or block.options.title == 'none':
        return None, NO_SPACING

    if block.options.title != 'simple':
        # warnings.warn(f"Border style '{block.options.title}' is not yet supported, treating as 'simple'")
        pass

    title_style = pdf.styles[block.options.title_style]

    title_bounds = title_style.box.inset_within_padding(inner)
    placed = place_run(block.title, title_bounds.extent, title_style, pdf)
    placed.location = title_bounds.top_left

    r1 = title_style.box.inset_within_margin(inner)
    r2 = title_style.box.outset_to_border(placed.bounds)
    plaque_rect = Rect(r1.left, r1.right, r2.top, r2.bottom)

    plaque = PlacedRectContent(plaque_rect.extent, plaque_rect.top_left, NO_ERROR, title_style)

    title_group = PlacedGroupContent.from_items([plaque, placed], plaque.extent)
    spacing = Spacing(top=plaque.extent.height + title_style.box.margin.vertical, left=0, right=0, bottom=0)
    return title_group, spacing


def locate_title(title: PlacedContent, block: Block, content_extent: Extent, pdf: PDF) -> None:
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
        return PlacedRectContent(bounds.extent, bounds.top_left, NO_ERROR, base_style)
    else:
        return None


def place_block(block: Block, size: Extent, pdf: PDF) -> PlacedContent:
    """ Margins have already been inset when we get into here"""

    main_style = pdf.styles[block.options.style]
    container = Rect(0, size.width, 0, size.height)

    # Create the title and insets to allow room for it
    title, title_spacing = make_title(block, container, pdf)

    if not block.children:
        if not title:
            raise RuntimeError('Need either a title or content in a block')
        else:
            return title

    # Reduce space for the items to account for the title
    inner_bounds = main_style.box.inset_from_margin_within_padding(container)
    item_bounds = inner_bounds - title_spacing

    placed_children = place_block_children(block, item_bounds, pdf)
    locate_title(title, block, placed_children.bounds, pdf)
    frame_bounds = main_style.box.outset_to_border(placed_children.bounds + title_spacing)

    frame = make_frame(frame_bounds, main_style)

    # Make the valid items
    items = [i for i in (frame, placed_children, title) if i]
    if len(items) == 1:
        return items[0]
    return PlacedGroupContent.from_items(items)


def place_block_children(block, item_bounds: Rect, pdf) -> Optional[PlacedGroupContent]:
    if not block.children:
        return None
    content_style = pdf.styles[block.options.style]
    padding = content_style.box.padding
    inter_cell_spacing_horizontal = max(padding.left, padding.right)
    inter_cell_spacing_vertical = max(padding.top, padding.bottom)

    # Count the columns
    ncols = max(len(item.children) for item in block.children)

    chooser = ColumnWidthChooser(0, item_bounds.width, inter_cell_spacing_horizontal, ncols)
    divisions = chooser.divisions()

    best = None
    for div in divisions:
        next_top = 0
        column_sizes = chooser.divide_width(div)

        try:
            placed_items = []
            for item in block.children:
                row_bottom = next_top
                for i, run in enumerate(item.children):
                    left = column_sizes[i].left
                    right = column_sizes[i].right
                    cell_rect = Rect(left, right, next_top, item_bounds.bottom)
                    placed_run = place_run(run, cell_rect.extent, content_style, pdf)
                    placed_run.location = cell_rect.top_left
                    row_bottom = max(row_bottom, placed_run.bounds.bottom)
                    placed_items.append(placed_run)
                next_top = row_bottom + inter_cell_spacing_vertical
            # We added an extra gap that we now remove to give the true bottom, and then add bottom margin
            block_bottom = next_top - inter_cell_spacing_vertical
            extent = Extent(item_bounds.width, block_bottom)
            placed_children = PlacedGroupContent.from_items(placed_items, extent)
            placed_children.location = item_bounds.top_left
            if placed_children.better(best):
                print('BEST', column_sizes, div)
                best = placed_children
        except PlacementError:
            pass

    return best
