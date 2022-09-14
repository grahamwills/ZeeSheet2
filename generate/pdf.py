import reprlib
import warnings
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import List, Tuple, Union, Dict

from reportlab.lib import colors
from reportlab.lib.colors import Color, toColor
from reportlab.pdfgen import canvas

from common import Rect, Point
from common import configured_logger
from generate.fonts import Font, FontLibrary
from structure.model import checkbox_character
from structure.style import Style, Defaults

LOGGER = configured_logger(__name__)

_WHITE = colors.Color(1, 1, 1)


class DrawMethod(Enum):
    FILL = 1
    DRAW = 2
    BOTH = 3


@dataclass
class TextSegment:
    text: str
    offset: Point
    font: Font

    def __str__(self):
        return reprlib.repr(self.text) + '@' + str(self.offset)


@dataclass
class CheckboxSegment:
    state: bool
    offset: Point
    font: Font

    def __str__(self):
        return checkbox_character(self.state) + '@' + str(self.offset)


class PDF(canvas.Canvas):

    def __init__(self,
                 pagesize: Tuple[int, int],
                 font_lib: FontLibrary,
                 styles: Dict[str, Style],
                 debug: bool = False) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.font_lib = font_lib
        self.setLineJoin(1)
        self.setLineCap(1)
        self.styles = styles
        self.debug = debug

        # Keep an index to give unique names to form items
        self._name_index = 0

    def get_font(self, style: Style) -> Font:
        try:
            font = self.font_lib.get_font(style.font.family, style.font.size, bold=style.font.is_bold,
                                          italic=style.font.is_italic)
        except KeyError:
            sim = self.font_lib.similar_names(style.font.family)
            if len(sim) == 1:
                warnings.warn(f"Unknown font family '{style.font.family}'. "
                              f"Using similarly-named family '{sim[0]}' instead")
            else:
                ss = ', '.join("'" + s + "'" for s in sim)
                warnings.warn(f"Unknown font family '{style.font.family}'. Did you mean one of {ss}? "
                              f"Using '{sim[0]}' instead")
            font = self.font_lib.get_font(sim[0], style.font.size, bold=style.font.is_bold, italic=style.font.is_italic)
        return font.standardize()

    def get_text_color(self, style: Style) -> Color:
        s = style.text.color
        if s[0] == '#' and len(s) == 4:
            # Also handle the '#RGB' format
            c = '#' + s[1] + s[1]+ s[2]+ s[2]+ s[3]+ s[3]
        c = toColor(style.text.color)
        if style.text.opacity == 1.0:
            return c
        else:
            return Color(c.red, c.green, c.blue, c.alpha * style.text.opacity)

    def draw_rect(self, r: Rect, method: DrawMethod):
        self.rect(r.left, r.top, r.width, r.height,
                  fill=(method != DrawMethod.DRAW), stroke=(method != DrawMethod.FILL))

    def _draw_checkbox(self, rx, ry, font: Font, state, color: Color):
        size = font.ascent + font.descent

        x, y = self.absolutePosition(rx, ry + size)
        y = self._pagesize[1] - y
        self._name_index += 1
        name = 'f' + str(self._name_index)
        LOGGER.debug("Adding checkbox name='%s' with state=%s ", name, state)
        self.acroForm.checkbox(name=name, x=x, y=y, size=size,
                               fillColor=_WHITE, borderColor=color,
                               buttonStyle='cross', borderWidth=0.5, checked=state)

    def draw_text(self, style: Style, segments: List[Union[TextSegment, CheckboxSegment]]):
        ss = ', '.join([str(s) for s in segments])
        LOGGER.debug(f"Drawing segments {ss}")

        font = self.get_font(style)
        text = self.beginText()
        text.setTextOrigin(0, font.top_to_baseline)
        text_color = self.get_text_color(style)
        text.setFillColor(text_color)
        off = Point(0, 0)
        current_font = None
        for segment in segments:
            if segment.font != current_font:
                current_font = segment.font
                text.setFont(current_font.name, current_font.size, current_font.line_spacing)
            if segment.offset:
                text.moveCursor(segment.offset.x - off.x, segment.offset.y - off.y)
                off = segment.offset
            if hasattr(segment, 'text'):
                # It is text, so just output it
                text.textOut(segment.text)
            else:
                self._draw_checkbox(segment.offset.x, segment.offset.y, current_font, segment.state, text_color)

        self.drawText(text)

    def output(self) -> bytes:
        self.save()
        bytes = self.buffer.getvalue()
        self.buffer.close()
        return bytes
