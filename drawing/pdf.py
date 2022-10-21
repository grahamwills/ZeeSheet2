import colorsys
import pathlib
import reprlib
import warnings
from collections import defaultdict
from copy import copy
from io import BytesIO
from typing import List, Tuple, Dict, Optional

import PIL.Image
from PIL import ImageEnhance
from PIL.Image import Image
from reportlab.graphics.shapes import Path
from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from common import Rect, Point
from common import configured_logger
from drawing import Font, FontLibrary
from structure import Style
from structure import checkbox_character, ImageDetail

LOGGER = configured_logger(__name__)

_WHITE = colors.Color(1, 1, 1)

IMAGES_DIR = pathlib.Path(__file__).parent / 'resources' / 'images'
_MISSING_IMAGE_DATA = PIL.Image.open(IMAGES_DIR / 'missing icon.jpg')
_MISSING_IMAGE_DATA.load()
_MISSING_IMAGE = ImageDetail(-1, _MISSING_IMAGE_DATA, _MISSING_IMAGE_DATA.width, _MISSING_IMAGE_DATA.height)


class Segment:
    x: float
    y: float
    width: float
    font: Font
    color: Color

    @property
    def right(self):
        return self.x + self.width

    def __init__(self, x: float, y: float, width: float, font: Font, color: Color):
        self.x = x
        self.y = y
        self.width = width
        self.font = font
        self.color = color


class TextSegment(Segment):
    text: str

    def __init__(self, text: str, x: float, y: float, width: float, font: Font, color: Color):
        super().__init__(x, y, width, font, color)
        self.text = text

    def __str__(self):
        return reprlib.repr(self.text) + f"@{round(self.x)},{round(self.y)}-{round(self.width)}"

    def to_text(self):
        return self.text


class CheckboxSegment(Segment):
    state: bool

    def __init__(self, state: bool, x: float, y: float, width: float, font: Font, color: Color):
        super().__init__(x, y, width, font, color)
        self.state = state

    def __str__(self):
        return checkbox_character(self.state) + f"@{round(self.x)},{round(self.y)}-{round(self.width)}"

    def to_text(self):
        return '\u2612' if self.state else '\u2610'


class TextFieldSegment(Segment):
    text: str
    expands: bool

    def __init__(self, text: str, x: float, y: float, font: Font, color: Color):
        super().__init__(x, y, 0, font, color)
        c = text[0]
        if c == text[-1] and c in '-=':
            self.text = text.strip(c)
            self.expands = True
        else:
            self.text = text
            self.expands = False
        # Add a bit for the spacing around the field
        self.width = font.width(self.text) + 4


    def __str__(self):
        return 'TEXTFIELD' + f"@{round(self.x)},{round(self.y)}-{round(self.width)}"

    def to_text(self):
        if self.expands:
            return '[[--' + self.text + '--]]'
        else:
            return '[[ ' + self.text + ' ]]'


class PDF(canvas.Canvas):

    def __init__(self,
                 pagesize: Tuple[int, int],
                 font_lib: FontLibrary,
                 styles: Dict[str, Style],
                 images: Dict[str, ImageDetail] = None,
                 debug: bool = False) -> None:
        self.buffer = BytesIO()
        super().__init__(self.buffer, pagesize=pagesize, bottomup=0)
        self.font_lib = font_lib
        self.setLineJoin(1)
        self.setLineCap(1)
        self.styles = styles
        self.images = images or {}
        self.debug = debug

        # Caching of built objects.
        self.caches = defaultdict(lambda: None)

        # Keep an index to give unique names to form items
        self._name_index = 0

        # Set defaults
        self.setLineCap(2)
        self.setLineJoin(0)

    def get_font(self, style: Style) -> Font:
        font = self.font_lib.get_font(style.font.family, style.font.size, style.font.face)

        # Apply line spacing modifier if defined
        if style.font.spacing != 1:
            font = copy(font)
            font.line_spacing *= style.font.spacing
        return font

    def draw_path(self, path: Path, style: Style):
        LOGGER.debug("Drawing path")
        stroke_color = style.get_color(border=True)
        stroke_width = style.box.width
        self.setStrokeColor(stroke_color)
        self.setLineWidth(stroke_width)
        stroked = stroke_width > 0 and stroke_color.alpha > 0

        fill_color = style.get_color(box=True)
        self.setFillColor(fill_color)
        filled = fill_color.alpha > 0
        if stroked or filled:
            self.drawPath(path, fill=filled, stroke=stroked)

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
        if not stroked and not filled:
            return
        if base_style.box.effect == 'rounded':
            radius = min(base_style.box.effect_size, r.width / 2, r.height / 2)
            self.roundRect(r.left, r.top, r.width, r.height, radius, fill=filled, stroke=stroked)
        else:
            self.rect(r.left, r.top, r.width, r.height, fill=filled, stroke=stroked)

    def _draw_checkbox(self, rx, ry, font: Font, state: bool, color: Color):
        size = (font.ascent + font.descent) * 0.8
        x, y = self.absolutePosition(rx, ry + font.line_spacing / 2 + size / 2)
        y = self._pagesize[1] - y
        self._name_index += 1
        name = 'f' + str(self._name_index)
        LOGGER.debug("Adding checkbox name='%s' with state=%s ", name, state)
        self.acroForm.checkbox(name=name, x=x, y=y, size=size,
                               fillColor=_WHITE, borderColor=color,
                               buttonStyle='cross', borderWidth=0.5, checked=state)

    def _draw_textfield(self, content: str, rx, ry, width, font: Font, color: Color):

        if font.name not in self.acroForm.formFontNames:
            if font.family.category == 'serif':
                fname = 'Times-Roman'
                draw_font = self.font_lib.get_font('Times', font.size)
                height = draw_font.line_spacing
            else:
                fname = 'Helvetica'
                draw_font = self.font_lib.get_font('Helvetica', font.size)
                height = draw_font.line_spacing
        else:
            fname = font.name
            height = font.line_spacing

        x, y = self.absolutePosition(rx, ry + font.line_spacing / 2 + height / 2)
        y = self._pagesize[1] - y
        self._name_index += 1
        name = 'f' + str(self._name_index)
        LOGGER.debug("Adding text field name='%s'", name)

        bg = _adapt_color_value(color, 0.9, alpha=0.25)
        border = _adapt_color_value(color, 0.2, alpha=0.8)

        self.acroForm.textfield(name=name, value=content, x=x, y=y - 1, relative=False,
                                width=width, height=height + 2,
                                fontName=fname, fontSize=font.size, textColor=color,
                                fillColor=bg, borderWidth=0.3333, borderColor=border)

    def draw_text(self, style: Style, segments: List[Segment]):
        ss = ', '.join([str(s) for s in segments])
        LOGGER.debug(f"Drawing segments {ss}")

        font = self.get_font(style)
        text = self.beginText()
        text.setTextOrigin(0, font.top_to_baseline)
        text_color = None
        off = Point(0, 0)
        current_font = None
        for seg in segments:
            if seg.font != current_font:
                current_font = seg.font
                text.setFont(current_font.name, current_font.size, current_font.line_spacing)
            text.moveCursor(seg.x - off.x, seg.y - off.y)
            off = Point(seg.x, seg.y)
            if isinstance(seg, TextSegment):
                # It is text, so just output it
                if seg.color != text_color:
                    text_color = seg.color
                    text.setFillColor(text_color)
                text.textOut(seg.text)
            elif isinstance(seg, CheckboxSegment):
                # Check Box
                self._draw_checkbox(seg.x, seg.y, current_font, seg.state, seg.color)
            else:
                # Text field
                self._draw_textfield(seg.text.strip(), seg.x, seg.y, seg.width, current_font, seg.color)

        self.drawText(text)

    def output(self) -> bytes:
        self.save()
        bytes_data = self.buffer.getvalue()
        self.buffer.close()
        return bytes_data

    def __hash__(self):
        return id(self)

    def get_image(self, image_name) -> Optional[ImageDetail]:
        if not image_name:
            return None
        try:
            return self.images[str(image_name)]
        except KeyError:
            warnings.warn(f"Image with index '{image_name}' was requested, but has not been defined for this sheet. "
                          "Use the Sheet Details button to upload images")
            return _MISSING_IMAGE

    def draw_image(self, image: Image, bounds: Rect, brightness: float, contrast: float):

        if contrast != 1:
            image = ImageEnhance.Contrast(image).enhance(contrast)
        if brightness != 1:
            image = ImageEnhance.Brightness(image).enhance(brightness)

        # Invert to fix the coordinate system which has already been inverted
        self.translate(bounds.left, bounds.top)
        self.transform(1, 0, 0, -1, 0, bounds.height)
        self.drawImage(ImageReader(image), 0, 0, bounds.width, bounds.height)

    def style(self, style_name: str, default='default'):
        try:
            return self.styles[style_name]
        except KeyError:
            warnings.warn(f"Style '{style_name}' was not defined, using '{default}' instead")
            try:
                return self.styles[default]
            except KeyError:
                raise RuntimeError(f"Default style '{default}' was not found")


def _adapt_color_value(c: Color, value: float, alpha: float = 1.0) -> Color:
    h, l, s = colorsys.rgb_to_hls(*c.rgb())
    r, g, b = (i for i in colorsys.hls_to_rgb(h, value, s))
    return Color(r, g, b, alpha * c.alpha)
