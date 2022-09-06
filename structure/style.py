from __future__ import annotations

from dataclasses import dataclass, field

from reportlab.lib import units
from reportlab.lib.colors import Color, toColor

from common import Spacing


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


@dataclass
class FontStyle:
    family: str = None
    size: float = None
    style: str = None

    def set(self, name: str, value):
        key = name.lower().replace('-', '_')
        if key in ['font', 'fontfamily', 'family']:
            self.family = value
        elif key == 'size':
            self.size = float(value)
        elif key in ['style', 'face']:
            if value.lower() in {'normal', 'regular', 'bold', 'italic', 'bolditalic'}:
                self.align = value.lower()
            else:
                raise ValueError(
                    f"Unknown value {value} for alignment -- should be one of: regular, bold, italic, boldItalic")
        else:
            raise AttributeError(key)


@dataclass
class TextStyle:
    color: Color = None
    opacity: float = None
    align: str = None
    indent: float = None

    def set(self, name: str, value):
        key = name.lower().replace('-', '').replace('_', '')
        if key.startswith('text'):
            key = key[4:]
        if key in ['color', 'foreground']:
            self.color = toColor(value)
        elif key == 'opacity':
            self.opacity = float(value)
        elif key == 'align':
            if value in {'left', 'right', 'center'}:
                self.align = value
            else:
                raise ValueError(f"Unknown value {value} for alignment -- should be one of: left, right, center")
        elif key in ['indent', 'indentation']:
            self.indent = float(value)
        else:
            raise AttributeError(key)


@dataclass
class BoxStyle:
    border: str = None
    width: float = None
    color: Color = None
    opacity: float = None
    margin: Spacing = None
    padding: Spacing = None

    def set(self, name: str, value):
        key = name.lower().replace('-', '').replace('_', '')
        if key.startswith('box'):
            key = key[3:]
        if key in {'color', 'backgroundcolor'}:
            self.color = toColor(value)
        elif key in {'opacity', 'backgroundopacity'}:
            self.opacity = float(value)
        elif key in {'border', 'method', 'style'}:
            if value in {'none', 'square', 'rounded'}:
                self.border = value
            else:
                raise ValueError(f"Unknown value {value} for border -- should be one of: none, square, rounded")
        elif key == 'margin':
            self.margin = text_to_spacing(value)
        elif key == 'padding':
            self.padding = text_to_spacing(value)
        elif key in ['width', 'size', 'linewidth']:
            self.width = units.toLength(value)
        else:
            raise AttributeError(key)


@dataclass
class Style:
    """ A complete style  """
    name: str
    parent: Style
    text: TextStyle = field(default_factory=TextStyle)
    font: FontStyle = field(default_factory=FontStyle)
    box: BoxStyle = field(default_factory=BoxStyle)

    def set(self, key: str, value: str):
        children = ('text', 'font', 'box')

        # Check if the attribute has a child name as prefix
        for child in children:
            if key.startswith(child):
                getattr(self, child).set(key[len(key):], value)

        # Just try the children in order. The order is important as
        # the children may have attributes with the same name
        for child in children:
            try:
                getattr(self, child).set(key, value)
            except AttributeError:
                pass

        raise AttributeError(key)


class Default:
    """ Default Values """

    # noinspection PyTypeChecker
    base = Style(
        'default',
        None,
        TextStyle(Color(0, 0, 0), 1.0, 'left', 0),
        FontStyle('Helvetica', 12, 'normal'),
        BoxStyle('none', 1, Color(1, 1, 1), 0.0, Spacing.balanced(0), Spacing.balanced(0)))


def set_style_value(obj, name: str, value: str):
    # First standardize the name
    name = name.lower().replace('-', '_')

    # If this works, great
    if hasattr(obj, name):
        setattr(obj, name, value)
        return

    # See if we need to set a value on a child
    try:
        p = name.index('-')
        if hasattr(obj, name[:p]):
            set_style_value(getattr(obj, name[:p]), name[p + 1:], value)
    except ValueError:
        pass
