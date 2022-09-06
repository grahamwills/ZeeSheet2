from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from reportlab.lib import units
from reportlab.lib.colors import toColor

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

    def set(self, key: str, value):
        if key in ['font', 'fontfamily', 'family']:
            self.family = value
        elif key == 'size':
            self.size = float(value)
        elif key in ['style', 'face']:
            if value.lower() in {'normal', 'regular', 'bold', 'italic', 'bolditalic'}:
                self.style = value.lower()
            else:
                raise ValueError(
                    f"Unknown value {value} for alignment -- should be one of:regular, bold, italic, boldItalic")
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.family:
            parts.append(f'font-family:{self.family}')
        if self.size is not None:
            parts.append(f'font-size:{self.size}')
        if self.style is not None:
            parts.append(f'font-style:{self.style}')


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
            toColor(value)  # Check it is valid
            self.color = value
        elif key == 'opacity':
            self.opacity = float(value)
        elif key == 'align':
            if value in {'left', 'right', 'center'}:
                self.align = value
            else:
                raise ValueError(f"Unknown value {value} for alignment -- should be one of:left, right, center")
        elif key in ['indent', 'indentation']:
            self.indent = float(value)
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.color:
            parts.append(f'text-color:{self.color}')
        if self.opacity is not None:
            parts.append(f'text-opacity:{self.opacity}')
        if self.align is not None:
            parts.append(f'text-align:{self.align}')
        if self.indent is not None:
            parts.append(f'text-indent:{self.indent}')


def _len2str(x: float) -> str:
    if x == 0:
        return 0
    if x % 9 == 0:
        return f'{x / 9}in'
    elif x == int(x):
        return str(int(x))
    else:
        return str(x)


def spacing_to_text(spacing: Spacing) -> str:
    parts = (_len2str(spacing.left), _len2str(spacing.right), _len2str(spacing.top), _len2str(spacing.bottom))
    if parts[0] == parts[1] == parts[2] == parts[3]:
        return '{}'.format(parts[0])
    if parts[0] == parts[1] and  parts[2] == parts[3]:
        return '{} {}'.format(parts[0], parts[1])
    else:
        return '{} {} {} {}'.format(*parts)


@dataclass
class BoxStyle:
    color: str = None
    opacity: float = None
    border: str = None
    width: float = None
    border_color: str = None
    border_opacity: float = None
    margin: Spacing = None
    padding: Spacing = None

    def set(self, key: str, value):
        if key.startswith('box'):
            key = key[3:]
        if key in {'color', 'backgroundcolor', 'background', 'bg'}:
            toColor(value)  # Check it is valid
            self.color = value
        elif key in {'opacity', 'backgroundopacity', 'bgopacity'}:
            self.opacity = float(value)
        if key == 'bordercolor':
            toColor(value)  # Check it is valid
            self.border_color = value
        if key == 'borderopacity':
            toColor(value)  # Check it is valid
            self.border_opacity = value
        elif key in {'border', 'method', 'style'}:
            if value in {'none', 'square', 'rounded'}:
                self.border = value
            else:
                raise ValueError(f"Unknown value {value} for border -- should be one of:none, square, rounded")
        elif key == 'margin':
            self.margin = text_to_spacing(value)
        elif key == 'padding':
            self.padding = text_to_spacing(value)
        elif key in ['width', 'size', 'linewidth', 'borderwidth']:
            self.width = units.toLength(value)
        else:
            raise AttributeError(key)

    def add_to_definition(self, parts: List[str]) -> None:
        if self.border:
            parts.append(f'border:{self.border}')
        if self.width:
            parts.append(f'border-width:{self.width}')
        if self.border_color:
            parts.append(f'border-color:{self.border_color}')
        if self.border_opacity is not None:
            parts.append(f'border-opacity:{self.border_opacity}')
        if self.color:
            parts.append(f'background-color:{self.color}')
        if self.opacity is not None:
            parts.append(f'background-opacity:{self.opacity}')
        if self.margin is not None:
            parts.append(f'margin:{spacing_to_text(self.margin)}')
        if self.padding is not None:
            parts.append(f'indent:{spacing_to_text(self.padding)}')


@dataclass
class Style:
    """ A complete style  """
    name: str
    parent: str = None
    text: TextStyle = field(default_factory=TextStyle)
    font: FontStyle = field(default_factory=FontStyle)
    box: BoxStyle = field(default_factory=BoxStyle)

    def __post_init__(self):
        if not self.name.isidentifier():
            raise ValueError(f'Style name must be a valid identifier, but was {self.name}')

    def set(self, key: str, value: str):
        key = key.lower().replace('-', '').replace('_', '')
        if key in {'parent', 'inherit'}:
            self.parent = value

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

    def to_definition(self):
        parts = []
        if self.parent:
            parts.append(f'inherit:{self.parent}')
        self.text.add_to_definition(parts)
        self.font.add_to_definition(parts)
        self.box.add_to_definition(parts)
        return '; '.join(parts)


class Defaults:
    """ Default Values """

    # noinspection PyTypeChecker
    base = Style(
        'default',
        None,
        TextStyle('black', 1.0, 'left', 0),
        FontStyle('Helvetica', 12, 'normal'),
        BoxStyle(
            'white', 0.0,
            'none', 1, 'black', 1.0,
            Spacing.balanced(0), Spacing.balanced(0)))


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
