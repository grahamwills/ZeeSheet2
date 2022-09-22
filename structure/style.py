from __future__ import annotations

import colorsys
from dataclasses import dataclass, field
from typing import List, Iterable, Optional, Union
from warnings import warn

import reportlab.lib.colors
from reportlab.lib import units
from reportlab.lib.colors import Color

import common
from common import Spacing, Rect, Extent
from common.logging import message_unknown_attribute, message_bad_value, configured_logger

LOGGER = configured_logger(__name__)

_TRANSPARENT = Color(1, 1, 1, 0)


def _q(txt: str) -> str:
    if ' ' in txt:
        return "'" + txt + "'"
    else:
        return txt


def _check_valid_color(name: str):
    """ raises a key error if the name is not found"""
    name = name.lower()
    if name not in {'none', 'auto'}:
        reportlab.lib.colors.toColor(name)


def _brightness(c: Color) -> bool:
    """ Returns true if the color is mostly lighter"""

    # Assuem the background is light if we have an alpha value
    base = (0.299 * c.red ** 2 + 0.587 * c.green ** 2 + 0.114 * c.blue ** 2) ** 0.5
    return base * c.alpha + (1 - c.alpha)


def _modify_brightness(c: Color, value: float) -> str:
    h, l, s = colorsys.rgb_to_hls(*c.rgb())
    r, g, b = (round(i * 255) for i in colorsys.hls_to_rgb(h, value, s))
    return f'#{r:02x}{g:02x}{b:02x}'


def _is_grayscale(c: Color) -> bool:
    h, s, v = colorsys.rgb_to_hsv(*c.rgb())
    return s < 0.2


def text_to_spacing(text: str) -> Spacing:
    # Convert to units
    if isinstance(text, Spacing):
        return text
    d = [units.toLength(s) for s in text.split()]
    if len(d) == 1:
        return Spacing(d[0], d[0], d[0], d[0])
    if len(d) == 2:
        return Spacing(d[0], d[0], d[1], d[1])
    if len(d) == 4:
        return Spacing(d[0], d[1], d[2], d[3])
    raise ValueError('Lengths must be a single item, 2 items or all four')


def validate_value(key: str, value: str, possibles: Iterable[str]):
    if value.lower() not in possibles:
        p = ', '.join(possibles)
        raise ValueError(f"'{value}' is not a legal value for the style attribute {key}. Should be one of {p}")


@dataclass
class FontStyle:
    family: str = None
    size: float = None
    style: str = None

    def set(self, key: str, value):
        FACES = ('normal', 'regular', 'bold', 'italic', 'bolditalic')
        if key in ['font', 'fontfamily', 'family']:
            self.family = value
        elif key == 'size':
            self.size = float(value)
        elif value is None and key.lower() in FACES:
            self.style = key.lower()
        elif key in ['style', 'face']:
            validate_value(key, value, FACES)
            self.style = value.lower()
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.family:
            parts.append(f'font-family:{_q(self.family)}')
        if self.size is not None:
            parts.append(f'font-size:{num2str(self.size)}')
        if self.style is not None:
            parts.append(f'font-style:{self.style}')

    @property
    def is_bold(self):
        return 'bold' in self.style

    @property
    def is_italic(self):
        return 'italic' in self.style


@dataclass
class TextStyle:
    color: str = None
    opacity: float = None
    align: str = None
    indent: float = None

    def set(self, key: str, value):
        if key.startswith('text'):
            key = key[4:]
        if key in ['color', 'foreground']:
            _check_valid_color(value)  # Check it is valid
            self.color = value
        elif key == 'opacity':
            self.opacity = txt2fraction(value)
        elif key in {'align', 'alignment'}:
            validate_value(key, value, ('left', 'right', 'center'))
            self.align = value
        elif key in ['indent', 'indentation']:
            self.indent = units.toLength(value)
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.color:
            parts.append(f'text-color:{self.color}')
        if self.opacity is not None:
            parts.append(f'text-opacity:{num2str(self.opacity)}')
        if self.align is not None:
            parts.append(f'text-align:{self.align}')
        if self.indent is not None:
            parts.append(f'text-indent:{num2str(self.indent)}')


def spacing_to_text(spacing: Spacing) -> str:
    parts = (len2str(spacing.left), len2str(spacing.right), len2str(spacing.top), len2str(spacing.bottom))
    if parts[0] == parts[1] == parts[2] == parts[3]:
        return '{}'.format(parts[0])
    if parts[0] == parts[1] and parts[2] == parts[3]:
        return "'{} {}'".format(parts[0], parts[2])
    else:
        return "'{} {} {} {}'".format(*parts)


@dataclass
class BoxStyle:
    color: str = None
    opacity: float = None
    width: float = None
    border_color: str = None
    border_opacity: float = None
    margin: Spacing = None
    padding: Spacing = None

    def set(self, key: str, value):
        if key.startswith('box'):
            key = key[3:]

        if key in {'color', 'backgroundcolor', 'background', 'bg'}:
            _check_valid_color(value)  # Check it is valid
            self.color = value
        elif key in {'opacity', 'backgroundopacity', 'bgopacity'}:
            self.opacity = txt2fraction(value)
        elif key == 'bordercolor' or key == 'border':
            _check_valid_color(value)  # Check it is valid
            self.border_color = value
        elif key == 'borderopacity':
            self.border_opacity = txt2fraction(value)
        elif key == 'margin':
            self.margin = text_to_spacing(value)
        elif key == 'padding':
            self.padding = text_to_spacing(value)
        elif key in ['width', 'size', 'linewidth', 'borderwidth', 'borderlinewidth']:
            self.width = units.toLength(value)
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.border_color:
            parts.append(f'border:{self.border_color}')
        if self.border_opacity is not None:
            parts.append(f'border-opacity:{num2str(self.border_opacity)}')
        if self.width:
            parts.append(f'border-width:{len2str(self.width)}')
        if self.color:
            parts.append(f'background:{self.color}')
        if self.opacity is not None:
            parts.append(f'background-opacity:{num2str(self.opacity)}')
        if self.margin is not None:
            parts.append(f'margin:{spacing_to_text(self.margin)}')
        if self.padding is not None:
            parts.append(f'padding:{spacing_to_text(self.padding)}')

    def has_border(self) -> bool:
        return self.border_color != 'none' and self.width > 0

    def inset_within_margin(self, e: Union[Extent, Rect]) -> Union[Extent, Rect]:
        """ Inset from the containers space to just inside the margin """
        return e - self.margin

    def inset_within_padding(self, e: Union[Extent, Rect]) -> Union[Extent, Rect]:
        """ Inset from the containers space to inside the margin, padding and border """
        base = e - (self.margin + self.padding)
        return base.pad(-self.width) if self.has_border() else base

    def inset_from_margin_within_padding(self, e: Union[Extent, Rect]) -> Union[Extent, Rect]:
        """ Given we have already applied margin, this applies the padding and border also """
        base = e - self.padding
        return base.pad(-self.width) if self.has_border() else base

    def outset_to_border(self, e: Union[Extent, Rect]) -> Union[Extent, Rect]:
        """ Take the inner content area and add padding and border """
        base = e + self.padding
        return base.pad(self.width) if self.has_border() else base

    def outset_to_margin(self, e: Union[Extent, Rect]) -> Union[Extent, Rect]:
        """ Take the inner content area and add margin, padding and border """
        base = e + self.margin + self.padding
        return base.pad(self.width) if self.has_border() else base


@dataclass
class Style:
    """ A complete style """
    name: str
    parent: str = None
    text: TextStyle = field(default_factory=TextStyle)
    font: FontStyle = field(default_factory=FontStyle)
    box: BoxStyle = field(default_factory=BoxStyle)

    def __post_init__(self):
        if not self.name.replace('-', '_').isidentifier():
            raise ValueError(f'Style name must be a valid identifier, but was {self.name}')

    def set(self, name: str, value: Optional[str]) -> Style:
        key = name.lower().replace('-', '').replace('_', '')
        if key in {'parent', 'inherit'}:
            self.parent = value
            return self

        children = ('text', 'font', 'box')

        try:
            # Check if the attribute has a child name as prefix
            for child in children:
                if key.startswith(child):
                    try:
                        getattr(self, child).set(key[len(child):], value)
                        return self
                    except AttributeError:
                        pass

            # Just try the children in order. The order is important as
            # the children may have attributes with the same name
            for child in children:
                try:
                    getattr(self, child).set(key, value)
                    return self
                except AttributeError:
                    pass

            warn(message_unknown_attribute(self.name, name, category='style'))
            return self
        except ValueError as ex:
            warn(message_bad_value(self.name, name, str(ex), category='style'))
            return self

    def get_color(self, box: bool = False, border: bool = False) -> Color:
        if border:
            name = self.box.border_color
            opacity = self.box.border_opacity
        elif box:
            name = self.box.color
            opacity = self.box.opacity
        else:
            name = self.text.color
            opacity = self.text.opacity

        if name.lower() == 'none':
            return _TRANSPARENT
        if name[0] == '#' and len(name) == 4:
            # Also handle the '#RGB' format
            name = '#' + name[1] + name[1] + name[2] + name[2] + name[3] + name[3]
        c: Color = reportlab.lib.colors.toColor(name)
        if opacity == 1.0 or opacity == None:
            return c
        else:
            return Color(c.red, c.green, c.blue, c.alpha * opacity)

    def to_definition(self):
        parts = []
        if self.parent:
            parts.append(f'inherit:{self.parent}')
        self.text.add_to_definition(parts)
        self.font.add_to_definition(parts)
        self.box.add_to_definition(parts)
        return ' '.join(parts)

    def __hash__(self):
        return id(self)


def set_using_definition(style: Style, text: str) -> None:
    for k, v in common.parse(text):
        style.set(k, v)


def txt2fraction(value: str) -> float:
    if value[-1] == '%':
        v = float(value[:-1]) / 100
    else:
        v = float(value)
    if 0 <= v <= 1:
        return v
    else:
        raise ValueError("Opacity must be in the range [0,1] or [0%, 100%]")


def num2str(x: float) -> str:
    if x == int(x):
        return str(int(x))
    else:
        # At most 2 decimal places
        return f'{x:.2f}'.rstrip('0')


def len2str(x: float) -> str:
    if x == 0:
        return 0
    if x % 72 == 0:
        return f'{int(x) // 72}in'
    if x % 9 == 0:
        return f'{int(x) / 72}in'
    return num2str(x)


# TODO: IDEA:  Set colors to auto and have them set automatically based on the other information


class Defaults:
    """ Default Values """

    DEFAULT_DARK = '#0074B7'
    DEFAULT_LIGHT = '#BFD7ED'

    DARK = 0.2
    BRIGHT = 1 - DARK

    # noinspection PyTypeChecker
    default = Style(
        'default',
        None,
        TextStyle('auto', 1.0, 'left', 0.0),
        FontStyle('Helvetica', 12.0, 'normal'),
        BoxStyle(
            'auto', 1.0,
            1.0, 'auto', 1.0,
            Spacing.balanced(0), Spacing.balanced(2)))

    title = Style('default-title').set('font-size', '14').set('font-face', 'bold').set('padding', '0')
    block = Style('default-block').set('margin', '12')
    section = Style('default-section').set('margin', '0').set('padding', '0') \
        .set('border','none').set('background', 'none')
    sheet = Style('default-sheet').set('padding', '0.25in').set('margin', '0') \
        .set('border','none').set('background', 'none')

    @classmethod
    def all(cls):
        return {s.name: s for s in [Defaults.default, Defaults.sheet, Defaults.block, Defaults.title, Defaults.section]}

    @classmethod
    def set_auto_text_box_border(cls, style: Style):
        if 'title' in style.name.lower():
            style.box.color = Defaults.DEFAULT_DARK
        elif 'block' in style.name.lower():
            style.box.color = Defaults.DEFAULT_LIGHT
        else:
            style.box.color = 'none'
        cls.set_auto_text_border(style)

    @classmethod
    def set_auto_text_border(cls, style: Style):
        bg = style.get_color(box=True)
        if _brightness(bg) > 0.5:
            style.text.color = 'black'
        else:
            style.text.color = 'white'
        cls.set_auto_border(style)

    @classmethod
    def set_auto_box_border(cls, style: Style):
        text = style.get_color()
        if _brightness(text) > 0.5:
            # Light text
            if _is_grayscale(text):
                style.box.color = 'black'
            else:
                style.box.color = _modify_brightness(text, value=Defaults.DARK)
        else:
            # Dark text
            if _is_grayscale(text):
                style.box.color = 'white'
            else:
                style.box.color = _modify_brightness(text, value=Defaults.BRIGHT)
        cls.set_auto_border(style)

    @classmethod
    def set_auto_text_box(cls, style: Style):
        border = style.get_color(border=True)
        if _brightness(border) > 0.5:
            # Light border
            if _is_grayscale(border):
                style.text.color = 'white'
            else:
                style.text.color = _modify_brightness(border, value=Defaults.BRIGHT)
        else:
            # Dark text
            if _is_grayscale(border):
                style.text.color = 'black'
            else:
                style.text.color = _modify_brightness(border, value=Defaults.DARK)
        cls.set_auto_box(style)

    @classmethod
    def set_auto_text(cls, style: Style):
        bg = style.get_color(box=True)
        border = style.get_color(border=True)
        # Set the text to match the border and contrast with the background
        if _brightness(bg) > 0.5:
            if _is_grayscale(border):
                style.text.color = 'black'
            else:
                style.text.color = _modify_brightness(border, value=Defaults.DARK)
        else:
            if _is_grayscale(border):
                style.text.color = 'white'
            else:
                style.text.color = _modify_brightness(border, value=Defaults.BRIGHT)

    @classmethod
    def set_auto_box(cls, style: Style):
        text = style.get_color()
        border = style.get_color(border=True)
        # Set the background to match the border and contrast with the text
        if _brightness(text) > 0.5:
            if _is_grayscale(border):
                style.box.color = 'black'
            else:
                style.box.color = _modify_brightness(border, value=Defaults.DARK)
        else:
            if _is_grayscale(border):
                style.box.color = 'white'
            else:
                style.box.color = _modify_brightness(border, Defaults.BRIGHT)

    @classmethod
    def set_auto_border(cls, style: Style):
        bg = style.get_color(box=True)
        if _brightness(bg) > 0.5:
            # Bright background, so make the border dark to contrast
            if _is_grayscale(bg):
                style.box.border_color = 'black'
            else:
                style.box.border_color = _modify_brightness(bg, value=Defaults.DARK)
        else:
            # Dark background, no border needed
            style.box.border_color = 'none'

    @classmethod
    def set_auto_values(cls, style: Style):
        method_extension = ''
        if style.text.color == 'auto':
            method_extension += '_text'
        if style.box.color == 'auto':
            method_extension += '_box'
        if style.box.border_color == 'auto':
            method_extension += '_border'

        # Call appropriate method
        if method_extension:
            method = getattr(cls, 'set_auto' + method_extension)
            method(style)
            LOGGER.debug(f'Set auto styles for {style.name}: '
                         f'txt={style.text.color}, bg={style.box.color}, bdr={style.box.border_color}')
