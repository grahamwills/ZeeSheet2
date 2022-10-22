from __future__ import annotations

import colorsys
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Iterable, Optional, Union
from warnings import warn

from reportlab.lib import units, colors

import common
from common import Spacing, Rect, Extent
from common.logging import message_unknown_attribute, message_bad_value, configured_logger

LOGGER = configured_logger(__name__)

_TRANSPARENT = colors.Color(1, 1, 1, 0)


# noinspection PyArgumentList,PyUnresolvedReferences
@lru_cache
def to_color(txt: str, opacity: float or None = None) -> colors.Color or None:
    txt = txt.lower()
    if len(txt) == 4 and txt[0] == '#':
        txt = '#' + txt[1] + txt[1] + txt[2] + txt[2] + txt[3] + txt[3]
    if txt == 'none':
        return _TRANSPARENT
    if txt == 'auto':
        # Not an error, but cannot be converted to a color
        return None
    color = colors.toColor(txt)
    if opacity == 1.0 or opacity is None:
        return color
    else:
        return colors.Color(color.red, color.green, color.blue, color.alpha * opacity)


def _brightness(c: colors.Color) -> bool:
    """ Returns true if the color is mostly lighter"""

    # Assume the background is light if we have an alpha value
    base = (0.299 * c.red ** 2 + 0.587 * c.green ** 2 + 0.114 * c.blue ** 2) ** 0.5
    return base * c.alpha + (1 - c.alpha)


def _modify_brightness(c: colors.Color, value: float) -> str:
    h, l, s = colorsys.rgb_to_hls(*c.rgb())
    if s > 0.1:
        s = 1.0
    r, g, b = (round(i * 255) for i in colorsys.hls_to_rgb(h, value, s))
    return f'#{r:02x}{g:02x}{b:02x}'


def _is_grayscale(c: colors.Color) -> bool:
    h, s, v = colorsys.rgb_to_hsv(*c.rgb())
    return s < 0.01


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


def text_to_fraction(text: str) -> float:
    if text.endswith('%'):
        return text_to_fraction(text[:-1]) / 100
    else:
        return float(text)


def validate_value(key: str, value: str, possibles: Iterable[str]):
    if value.lower() not in possibles:
        p = ', '.join(possibles)
        raise ValueError(f"'{value}' is not a legal value for the style attribute {key}. Should be one of {p}")


@dataclass
class Effect:
    name: str  # name
    needs_path_conversion: bool  # if true, rects need convertign to paths first
    needs_padding: bool  # space needed inside the usual frame
    size: float = None

    def sized(self, size: float) -> Effect:
        return Effect(self.name, self.needs_path_conversion, self.needs_padding, size)

    def padding(self) -> float:
        return self.size if self.needs_padding else 0


class Effects:
    NONE = Effect('none', False, False)
    ROUNDED = Effect('rounded', False, False)
    ROUGH = Effect('rough', True, True)
    COGS = Effect('cogs', True, True)
    ALL = {e.name: e for e in (NONE, ROUNDED, ROUGH, COGS)}


@dataclass
class FontStyle:
    FACES = ('normal', 'regular', 'bold', 'italic', 'bolditalic')

    family: str = None
    size: float = None
    face: str = None
    spacing: float = None

    # noinspection SpellCheckingInspection
    def set(self, key: str, value):
        if key in ['font', 'fontfamily', 'family']:
            self.family = value
        elif key == 'size':
            self.size = float(value)
        elif value is None and key.lower() in self.FACES:
            self.face = key.lower()
        elif key == 'spacing':
            self.spacing = text_to_fraction(value)
        elif key in ['style', 'face']:
            # Too many face options to validate
            self.face = value
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.family:
            parts.append(f'font-family:{_q(self.family)}')
        if self.size is not None:
            parts.append(f'font-size:{num2str(self.size)}')
        if self.face is not None:
            parts.append(f'font-face:{self.face}')
        if self.spacing is not None:
            s = common.to_str(self.spacing * 100, 1)
            parts.append(f'font-spacing:{s}%')

    @property
    def is_bold(self):
        return 'bold' in self.face

    @property
    def is_italic(self):
        return 'italic' in self.face


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
            to_color(value)  # Throws KeyError if it not a valid color
            self.color = value
        elif key == 'opacity':
            self.opacity = txt2fraction(value)
        elif key in {'align', 'alignment'}:
            validate_value(key, value, ('left', 'right', 'center', 'auto'))
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
    effect: str = None
    effect_size: float = None

    def set(self, key: str, value):
        if key.startswith('box'):
            key = key[3:]

        if key in {'color', 'backgroundcolor', 'background', 'bg'}:
            to_color(value)  # Check it is valid
            self.color = value
        elif key in {'opacity', 'backgroundopacity', 'bgopacity'}:
            self.opacity = txt2fraction(value)
        elif key == 'bordercolor' or key == 'border':
            to_color(value)  # Check it is valid
            self.border_color = value
        elif key == 'borderopacity':
            self.border_opacity = txt2fraction(value)
        elif key == 'margin':
            self.margin = text_to_spacing(value)
        elif key == 'padding':
            self.padding = text_to_spacing(value)
        elif key in ['width', 'size', 'linewidth', 'borderwidth', 'borderlinewidth']:
            self.width = units.toLength(value)
        elif key == 'effect':
            value = value.lower()
            validate_value(key, value, Effects.ALL.keys())
            self.effect = value
        elif key == 'effectsize':
            self.effect_size = units.toLength(value)
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
        if self.effect is not None:
            parts.append(f'effect:{self.effect}')
        if self.effect_size is not None:
            parts.append(f'effect-size:{len2str(self.effect_size)}')

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
        if not re.match('^[A-Za-z_][A-Za-z0-9_\\-\\.§]*$', self.name):
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

    def get_color(self, box: bool = False, border: bool = False) -> colors.Color:
        if border:
            name = self.box.border_color
            opacity = self.box.border_opacity
        elif box:
            name = self.box.color
            opacity = self.box.opacity
        else:
            name = self.text.color
            opacity = self.text.opacity
        return to_color(name, opacity)

    def get_effect(self) -> Effect:
        size = self.box.effect_size
        if size <= 0:
            return Effects.NONE
        base = Effects.ALL[self.box.effect]
        if base != Effects.NONE:
            base = base.sized(size)
        return base

    def to_definition(self):
        parts = []
        if self.parent:
            parts.append(f'inherit:{self.parent}')
        self.text.add_to_definition(parts)
        self.font.add_to_definition(parts)
        self.box.add_to_definition(parts)
        return ' '.join(parts)

    def __copy__(self) -> Style:
        result = Style(self.name)
        set_using_definition(result, self.to_definition())
        return result

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
        return '0'
    if x % 72 == 0:
        return f'{int(x) // 72}in'
    if x % 9 == 0:
        return f'{int(x) / 72}in'
    return num2str(x)


def process_definitions(name, parents, attrs):
    # Use the definitions to create a set of styles
    created = []
    for line in attrs['DEFINITIONS'].split('\n'):
        if not line.strip():
            continue
        parts = line.split('=')
        if len(parts) == 2:
            name = parts[0].strip()
            if name == 'default':
                created.append(Style(name))
            else:
                created.append(Style('default-' + name))
            attrs[name] = created[-1]

        set_using_definition(created[-1], parts[-1].strip())

    # Add the new styles to the attrs, and create new attrs to hold collections
    attrs['ALL'] = tuple(created)
    attrs['ALL_NAMES'] = tuple(s.name for s in created)

    return type(name, parents, attrs)


class StyleDefaults(metaclass=process_definitions):
    """ Default Values """

    DEFAULT_DARK = '#004166'
    DEFAULT_LIGHT = '#BFD7ED'

    DARK = 0.25
    BRIGHT = 1 - DARK

    DEFINITIONS = '''
        default =   inherit:# text-color:auto text-opacity:1 text-align:auto text-indent:4 
                    font:Montserrat font-size:10 font-face:Regular font-spacing:100%
                    box-color:auto box-opacity:1 box-width:1 box-border-color:auto box-border-opacity:1
                    box-margin:0 box-padding:2 effect:none effect-size:3
        title =     inherit:default font-size:11 font-face:bold padding:1
        block =     inherit:default margin:8
        section =   inherit:default margin:0 padding:0 border:none background:none
        image =     inherit:default-block inherit:default-block border:none background:none
        sheet =     inherit:default padding:0.25in margin:0 border:none background:none
        hidden =    inherit:default margin:0 padding:0 font-size:1 border:none 
        
        attributes =        inherit:default-block font-size:12 bg:#004166 padding:'6 4' align:auto box-effect:rounded
        attributes-title =  inherit:default-title font-size:22 margin:2 padding:6 text-color:yellow align:auto
    '''

    @classmethod
    def set_auto_text_box_border(cls, style: Style, target: str, pair: Style):
        # Try and base it on the pair first
        if pair:
            if 'title' in target:
                style.box.border_color = 'none'
                cls.set_auto_text_box(style, target, pair)
                return
            else:
                if pair.box.color != 'auto':
                    style.box.border_color = pair.box.color
                    cls.set_auto_text_box(style, target, pair)
                    return

        if 'title' in target:
            style.box.color = StyleDefaults.DEFAULT_DARK
        elif 'block' in target:
            style.box.color = StyleDefaults.DEFAULT_LIGHT
        else:
            style.box.color = 'none'
        cls.set_auto_text_border(style, target, pair)

    @classmethod
    def set_auto_text_border(cls, style: Style, target: str, pair: Style):
        bg = style.get_color(box=True)
        if _brightness(bg) > 0.5:
            style.text.color = 'black'
        else:
            style.text.color = 'white'
        cls.set_auto_border(style, target, pair)

    @classmethod
    def set_auto_box_border(cls, style, target: str, pair: Style):
        text = style.get_color()
        if _brightness(text) > 0.5:
            # Light text
            if _is_grayscale(text):
                style.box.color = 'black'
            else:
                style.box.color = _modify_brightness(text, value=StyleDefaults.DARK)
        else:
            # Dark text
            if _is_grayscale(text):
                style.box.color = 'white'
            else:
                style.box.color = _modify_brightness(text, value=StyleDefaults.BRIGHT)
        cls.set_auto_border(style, target, pair)

    @classmethod
    def set_auto_text_box(cls, style: Style, target: str, pair: Style):
        if pair:
            if 'title' in target:
                # Set the title's pair (should be a block) and then use that to set the title box color
                cls.set_auto_values(pair, 'block', None)
                if pair.box.border_color == 'none':
                    pair_bg = pair.get_color(box=True)
                    style.box.color = _modify_brightness(pair_bg, value=StyleDefaults.DARK)
                else:
                    style.box.color = pair.box.border_color
                cls.set_auto_text(style, target, pair)
                return
            else:
                if pair.box.color != 'auto':
                    pair_bg = pair.get_color(box=True)
                    style.box.color = _modify_brightness(pair_bg, value=StyleDefaults.BRIGHT)
                    cls.set_auto_text(style, target, pair)
                    return

        if style.box.border_color == 'none':
            if 'block' in target:
                style.box.color = StyleDefaults.DEFAULT_LIGHT
            elif 'title' in target:
                style.box.color = StyleDefaults.DEFAULT_DARK
            else:
                style.box.color = 'none'
            cls.set_auto_text(style, target, pair)
            return

        border = style.get_color(border=True)
        if _brightness(border) > 0.5:
            # Light border
            if _is_grayscale(border):
                style.text.color = 'white'
            else:
                style.text.color = _modify_brightness(border, value=StyleDefaults.BRIGHT)
        else:
            # Dark text
            if _is_grayscale(border):
                style.text.color = 'black'
            else:
                style.text.color = _modify_brightness(border, value=StyleDefaults.DARK)
        cls.set_auto_box(style, target, pair)

    @classmethod
    def set_auto_text(cls, style: Style, target: str, pair: Style):
        bg = style.get_color(box=True)
        # Set the text to contrast with the background
        back_bright = _brightness(bg)
        if back_bright > 0.5:
            c = pair.get_color(border=True) if pair else None
            if c and back_bright - _brightness(c) > 0.2:
                style.text.color = pair.box.border_color
            else:
                style.text.color = 'black'
        else:
            style.text.color = 'white'

    @classmethod
    def set_auto_box(cls, style: Style, *_):
        text = style.get_color()
        border = style.get_color(border=True)
        # Set the background to match the border and contrast with the text
        if _brightness(text) > 0.5:
            if _is_grayscale(border):
                style.box.color = 'black'
            else:
                style.box.color = _modify_brightness(border, value=StyleDefaults.DARK)
        else:
            if _is_grayscale(border):
                style.box.color = 'white'
            else:
                style.box.color = _modify_brightness(border, StyleDefaults.BRIGHT)

    @classmethod
    def set_auto_border(cls, style: Style, *_):
        if style.box.color == 'none':
            style.box.border_color = 'none'
            return
        bg = style.get_color(box=True)
        if _brightness(bg) > 0.5:
            # Bright background, so make the border dark to contrast
            if _is_grayscale(bg):
                style.box.border_color = 'black'
            else:
                style.box.border_color = _modify_brightness(bg, value=StyleDefaults.DARK)
        else:
            # Dark background, no border needed
            style.box.border_color = 'none'

    @classmethod
    def set_auto_values(cls, style: Style, target: str = 'default', pair: Style = None):
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
            method(style, target, pair)
            LOGGER.debug(f'Set auto styles for {style.name}: '
                         f'txt={style.text.color}, bg={style.box.color}, bdr={style.box.border_color}')


def _q(txt: str) -> str:
    if ' ' in txt:
        return "'" + txt + "'"
    else:
        return txt
