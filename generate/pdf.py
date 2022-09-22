import reprlib
import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import List, Tuple, Union, Dict, Any

from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.pdfgen import canvas

from common import Rect, Point
from common import configured_logger
from generate.fonts import Font, FontLibrary
from structure.model import checkbox_character
from structure.style import Style

LOGGER = configured_logger(__name__)

_WHITE = colors.Color(1, 1, 1)


@dataclass
class TextSegment:
    text: str
    offset: Point
    font: Font
    width: float

    def __str__(self):
        return reprlib.repr(self.text) + '@' + str(self.offset)

    def to_text(self):
        return self.text


@dataclass
class CheckboxSegment:
    state: bool
    offset: Point
    font: Font
    width: float

    def __str__(self):
        return checkbox_character(self.state) + '@' + str(self.offset)

    def to_text(self):
        return checkbox_character(self.state)

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

        # Set defaults
        self.setLineCap(2)
        self.setLineJoin(0)

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
        return font

    def _draw_rect(self, r: Rect, filled: int, stroked: int):
        self.rect(r.left, r.top, r.width, r.height, fill=filled, stroke=stroked)

    def draw_rect(self, r: Rect, base_style: Style):
        LOGGER.debug(f"Drawing {r} with style {base_style.name}")
        style = base_style.box
        stroke_color = base_style.get_color(border=True)
        stroke_width = style.width
        self.setStrokeColor(stroke_color)
        self.setLineWidth(stroke_width)
        stroked = stroke_width > 0 and stroke_color.alpha > 0
        fill_color = base_style.get_color(box=True)
        self.setFillColor(fill_color)
        filled = fill_color.alpha > 0
        if stroked or filled:
            self._draw_rect(r, filled=filled, stroked=stroked)

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
        text_color = style.get_color()
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
        bytes_data = self.buffer.getvalue()
        self.buffer.close()
        return bytes_data

    def __hash__(self):
        return id(self)
