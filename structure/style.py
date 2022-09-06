from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from reportlab.lib import units
from reportlab.lib.colors import Color, toColor

from common import Spacing


def text_to_spacing(text: str) -> Spacing:
    # Convert to units
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

    def __setattr__(self, name: str, value):
        key = name.lower().replace('-', '_')
        if key in ['font', 'font-family', 'family']:
            self.family = str(value)
        elif key == 'size':
            self.size = float(value)
        elif key in ['style', 'face']:
            self.style = str(value)
        else:
            raise AttributeError(key)


@dataclass
class TextStyle:
    color: Color = None
    opacity: float = None
    align: str = None
    indent: float = None

    def __setattr__(self, name: str, value):
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
class BorderStyle:
    method: str = None
    width: float = None
    color: Color = None
    opacity: float = None

    def __setattr__(self, name: str, value):
        key = name.lower().replace('-', '').replace('_', '')
        if key.startswith('border'):
            key = key[6:]
        if key == 'color':
            self.color = toColor(value)
        elif key == 'opacity':
            self.opacity = float(value)
        elif key in {'method', 'style', 'effect'}:
            if value in {'none', 'square', 'rounded'}:
                self.align = value
            else:
                raise ValueError(f"Unknown value {value} for alignment -- should be one of: none, square, rounded")
        elif key in ['width', 'size', 'linewidth']:
            self.width = units.toLength(value)
        else:
            raise AttributeError(key)


@dataclass
class BoxStyle:
    """ A complete style for a block, section or sheet"""
    name: str
    parent: Optional[BoxStyle]
    color: Color = None
    opacity: float = None
    border: BorderStyle = field(default_factory=BorderStyle)
    margin: Spacing = None
    padding: Spacing = None

    def __setattr__(self, name: str, value):
        key = name.lower().replace('-', '').replace('_', '')
        if key in {'color', 'backgroundcolor'}:
            self.color = toColor(value)
        elif key in {'opacity', 'backgroundopacity'}:
            self.opacity = float(value)
        elif key == 'border':
            setattr(self.border, key[6:], name)  # The child will handle it
        elif key in ['width', 'size']:
            self.width = float(value)
        elif key == 'margin':
            self.margin = text_to_spacing(value)
        elif key == 'padding':
            self.padding = text_to_spacing(value)
        else:
            raise AttributeError(key)


@dataclass
class RunStyle:
    """ A complete style for a run of text or text-like items """
    name: str
    parent: Optional[RunStyle]
    text: TextStyle = field(default_factory=TextStyle)
    font: FontStyle = field(default_factory=FontStyle)

    def __setattr__(self, name: str, value):
        # Get one of the two children to handle it, even if not properly scoped
        key = name.lower().replace('-', '').replace('_', '')
        if key == 'font':
            setattr(self.font, key[4:], name)
            return
        if key == 'text':
            setattr(self.text, key[4:], name)
            return
        try:
            setattr(self.text, key, name)
        except:
            pass
        try:
            setattr(self.font, key, name)
        except:
            pass
        raise AttributeError(key)


class Default:
    """ Default Values """
    run_style = RunStyle(
        'text',
        None,
        TextStyle(Color(0, 0, 0), 1.0, 'left', 0),
        FontStyle('Helvetica', 12, 'normal')
    )

    block_style = BoxStyle(
        'block',
        None,
        Color(1, 1, 1),
        1.0,
        BorderStyle('square', 5, 1, 'black', 0),
        Spacing.balanced(4),
        Spacing.balanced(2)
    )

    section_style = BoxStyle(
        'section',
        None,
        toColor('beige'),
        1.0,
        BorderStyle('none', 5, 1, 'black', 0),
        Spacing.balanced(8),
        Spacing.balanced(4)
    )

    sheet_style = BoxStyle(
        'sheet',
        None,
        Color(1, 1, 1),
        0.0,
        BorderStyle('none', 5, 1, 'black', 0),
        Spacing.balanced(1 * units.inch),
        Spacing.balanced(0.5 * units.inch)
    )


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
