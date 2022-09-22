from typing import Tuple

from common import Extent, Point
from generate.fonts import Font
from generate.pdf import TextSegment, CheckboxSegment, PDF
from layout.content import PlacementError, PlacedRunContent, ExtentTooSmallError
from structure import Run
from structure.style import Style


class RunBuilder:

    def __init__(self, run: Run, style: Style, extent: Extent, pdf: PDF):
        self.extent = extent
        self.elements = run.children
        self.style = style
        self.font = pdf.get_font(style)

    def build(self) -> PlacedRunContent:

        segments = []
        width = self.extent.width
        height = self.extent.height
        error = PlacementError(0, 0, 0)

        x = 0
        y = 0
        for element in self.elements:
            text = element.value
            modifier = element.modifier
            font = self.font.change_face(element.modifier == 'strong', element.modifier == 'emphasis')
            line_spacing = self.font.line_spacing

            while text:

                if x == 0 and y > 0:
                    # No leading white space on new lines
                    text = text.lstrip()
                    if not text:
                        break

                # If it does not fit vertically, record how much was clipped (in pixels) and do nothing else
                if y + line_spacing > height:
                    if y == 0:
                        raise ExtentTooSmallError(f'Height of {height} was too small to fit anything')
                    error.clipped += font.width(text) * line_spacing
                    text = None
                    continue

                if modifier == 'checkbox':
                    # Try to place checkbox on the line
                    checkbox_width = (font.ascent + font.descent) * 1.1
                    if x + checkbox_width <= width:
                        segments.append(CheckboxSegment(text == 'X', Point(x, y), font, checkbox_width))
                        x += checkbox_width
                        text = None

                else:
                    # Place as much text as possible on this line
                    text_width = font.width(text)
                    if x + text_width <= width:
                        # Happy path; it all fits
                        segments.append(TextSegment(text, Point(x, y), font, text_width))
                        x += text_width
                        text = None
                    else:
                        # Need to split the line
                        p, text_width, is_bad = self.split_text(text, font, width - x, text_width, x > 0)
                        if p > 0:
                            segments.append(TextSegment(text[:p].rstrip(), Point(x, y), font, text_width))
                            x += text_width
                            text = text[p:]
                            if is_bad:
                                error.bad_breaks += 1

                if text:
                    if x == 0:
                        # We were unable to place it and had the whole space to place into
                        raise ExtentTooSmallError(f"Could not fit '{text}' into {width}")
                    else:
                        # Start a new line
                        x = 0
                        y += line_spacing
                        error.breaks += 1

        last = segments[-1]
        right = max(s.offset.x + s.width for s in segments)
        bottom = max(s.offset.y + s.font.line_spacing for s in segments)
        extra_space = width - (last.offset.x + last.width)
        outer = Extent(right, bottom)

        error.breaks -= error.bad_breaks  # They have been double-counted
        return PlacedRunContent(outer, Point(0, 0), error, segments, self.style, extra_space)

    def split_text(self,
                   text: str,
                   font: Font,
                   width: float,
                   text_width: float,
                   only_at_whitespace
                   ) -> Tuple[int, float, bool]:
        """ Find a good splitting position for the text """

        n = len(text)

        # A guess at where we might find a good split
        guess = max(1, min(round(width * n / text_width), n - 2))

        # Step backwards through white spaces
        loc = 0
        wid = 0

        first = True
        for p in range(guess, 1, -1):
            if text[p].isspace() and not text[p + 1].isspace():
                w = font.width(text[:p])
                if w <= width:
                    loc = p
                    wid = w
                    break
                else:
                    first = False

        if loc:
            # We found a good breaking point
            if first:
                # There maybe one further ahead, so we need to keep looking and noting better break points
                for p in range(guess, n - 1):
                    if text[p].isspace() and not text[p + 1].isspace():
                        w = font.width(text[:p])
                        if w <= width:
                            loc = p
                            wid = w
                        else:
                            break

        if loc or only_at_whitespace:
            return loc, wid, False

        # Now try a break anywhere
        w = font.width(text[:guess])
        if w > width:
            # Search backwards until something fits
            for p in range(guess - 1, 0, -1):
                w = font.width(text[:p])
                if w <= width:
                    return p, w, True
        else:
            # Search forward while we have a good fit
            loc = guess
            wid = w
            for p in range(guess, n-1):
                w = font.width(text[:p])
                if w <= width:
                    loc = guess
                    wid = w
                else:
                    break

        return loc, wid, True
