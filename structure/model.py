from __future__ import annotations

import re
import warnings
from collections import namedtuple
from dataclasses import dataclass, field
from typing import List, Optional, ClassVar, Dict, Generator

from PIL.Image import Image
from reportlab.lib.units import inch

from .style import Style

FormatPieces = namedtuple('FormatInfo', 'open close sep')
Problem = namedtuple('Problem', 'lineNo is_error message')


def checkbox_character(state) -> str:
    if state == 'X' or state is True:
        return '\u2612'
    else:
        return '\u2610'


@dataclass
class CommonOptions:
    style: str = None
    image: int = 0
    image_mode: str = 'normal'
    image_width: float = None
    image_height: float = None
    image_anchor: str = None


@dataclass
class SheetOptions(CommonOptions):
    width: float = 8.5 * inch
    height: float = 11 * inch
    columns: int = 1
    quality: str = 'Medium'
    debug: bool = False

    def __post_init__(self):
        self.style = 'default-sheet'


@dataclass
class SectionOptions(CommonOptions):
    columns: int = 1


@dataclass
class BlockOptions(CommonOptions):
    method: str = 'table'
    title: str = None
    title_style: str = None


@dataclass
class ImageDetail:
    index: int
    data: Image
    width: int
    height: int

    def name(self):
        return 'Image#' + str(self.index)


@dataclass
class Generated:
    source: str
    value: str


@dataclass
class Element:
    value: str
    modifier: Optional[str] = None
    generated: Generated = None

    def __post_init__(self):
        assert self.value is not None, 'Element must be created with valid content'

    def description(self, short: bool):
        if short:
            if self.modifier == 'checkbox':
                return checkbox_character(self.value)
            if self.modifier == 'textfield':
                return '[[  ]]'
            return self.value if len(self.value) <= 20 else self.value[:19] + '\u2026'
        elif self.modifier:
            return '\u00ab' + self.value + '\u22a3' + self.modifier[:3] + '\u00bb'
        else:
            return self.value

    def to_rst(self):
        if self.modifier == 'strong':
            return '**' + self.value + '**'
        elif self.modifier == 'emphasis':
            return '*' + self.value + '*'
        elif self.modifier == 'literal':
            return '``' + self.value + '``'
        elif self.modifier == 'checkbox':
            return '[' + self.value + ']'
        elif self.modifier == 'textfield':
            return '[[' + self.value + ']]'
        elif self.modifier is None:
            return self.value
        else:
            raise ValueError('Unknown Element modifier: ' + self.modifier)

    @classmethod
    def _from_text(cls, txt):
        if txt == '[ ]' or txt == '[O]' or txt == '[o]':
            return cls(' ', 'checkbox')
        elif txt == '[X]' or txt == '[x]':
            return cls('X', 'checkbox')
        elif txt.startswith('[[') and txt.endswith(']]'):
            return cls(txt[2:-2], 'textfield')
        elif txt.startswith('``') and txt.endswith('``'):
            return cls(txt[2:-2], 'literal')
        else:
            return cls(txt, None)

    def as_simple_text(self):
        return self.value


# noinspection PyUnresolvedReferences,PyAttributeOutsideInit
@dataclass
class StructureUnit:
    FMT: ClassVar[FormatPieces]

    def __post_init__(self):
        self.name = None

    def __str__(self):
        return self.__class__.__name__

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item):
        return self.children[item]

    def _titled(self):
        return hasattr(self, 'title')

    def __bool__(self) -> bool:
        return bool(self.children) or (self._titled() and bool(self.title))

    def tidy(self, index: list[int]) -> None:
        raise NotImplementedError('Must be implemented by descendents')

    def _tidy_children(self, index: list[int], keep_empty: bool = False):
        """ Tidy children, and optionally throw away children with no content"""
        for i, s in enumerate(self.children):
            s.tidy(index + [i + 1])
        if not keep_empty:
            self.children = [s for s in self.children if s]

    def description(self, short: bool):
        start, sep, end = self.FMT

        title = self.title.description(short) + " ~ " if self._titled() and self.title else ''

        if short:
            content = str(len(self.children)) + " items"
        else:
            content = sep.join(s.description(short) for s in self.children)

        return start + (title + content).strip() + end


@dataclass
class Run(StructureUnit):
    FMT = FormatPieces('', '', '')
    children: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.children.append(element)

    def description(self, short: bool):
        if len(self.children) == 1:
            return self.children[0].description(short)
        else:
            return super().description(short)

    def to_rst(self, width: int = 9e99, indent: int = 0) -> str:
        if not self.children:
            return ''

        # Split plain text (no modifier elements) into words and create a list of all unsplittable units
        splitter = re.compile(r'(\S+)')
        atoms = []
        previous_generated = None
        for element in self.children:
            if element.generated:
                if element.generated == previous_generated:
                    # We have already added the referenced for this, so can skip this item
                    pass
                else:
                    # A new reference; we need to add it to the elements, with correct modifiers
                    if element.modifier == 'strong':
                        m = '**'
                    elif element.modifier == 'emphasis':
                        m = '*'
                    else:
                        m = ''
                    fake = Element(m + '{' + element.generated.source + '}' + m )
                    atoms.append(fake.to_rst())
                    previous_generated = element.generated
            elif element.modifier == 'literal':
                # Do not split literals
                atoms.append(element.to_rst())
            else:
                # Using explicit space to split keeps the whitespace around
                for w in splitter.split(element.to_rst()):
                    if w != '':
                        atoms.append(w)

        results = []
        current_line_length = indent
        for this, after in zip(atoms, atoms[1:] + [' ']):
            if this == ' ':
                # a potential break point
                if current_line_length + 1 + len(after) > width:
                    results.append('\n' + ' ' * indent)
                    current_line_length = indent
                else:
                    results.append(' ')
                    current_line_length += 1
            else:
                # Just add the item
                results.append(this)
                current_line_length += len(this)

        return ''.join(results)

    def as_simple_text(self):
        return ''.join(e.as_simple_text() for e in self.children)

    def tidy(self, index: list[int]) -> None:
        self.name = 'Run\u00a7' + '.'.join(str(x) for x in index)

    def strip(self):
        # Remove leading and trailing blanks
        if self.children:
            first = self.children[0]
            last = self.children[-1]
            if first.modifier is None:
                first.value = first.value.lstrip()
            if last.modifier is None:
                last.value = last.value.rstrip()

    def __hash__(self):
        return id(self)


@dataclass
class Item(StructureUnit):
    FMT = FormatPieces('[', ' \u2b29 ', ']')

    children: List[Run] = field(default_factory=lambda: [Run()])

    def as_str(self, width: int, indent: int = 0):
        assert len(self.children) == 1
        return self.children[0].to_rst(width, indent=indent)

    def add_to_content(self, element: Element):
        self.children[-1].append(element)

    def _split_run_into_cells(self, base: Run):
        self.children.append(Run())
        for element in base.children:
            if element.modifier or '|' not in element.value:
                # Does not contain a cell splitter
                self.add_to_content(element)
            else:
                generated = element.generated
                items = element.value.split('|')
                if items[0]:
                    # add the first one
                    self.add_to_content(Element(items[0], None, generated))
                for s in items[1:]:
                    # For the next items, start a new cell first
                    self.children.append(Run())
                    if s:
                        self.add_to_content(Element(s, None, generated))

    def tidy(self, index: list) -> None:
        self.name = 'Item\u00a7' + '.'.join(str(x) for x in index)
        # replace children with a new list, breaking runs into cells to do so

        old = self.children
        self.children = []
        for run in old:
            if run:
                self._split_run_into_cells(run)

        # Remove leading and trailing white space in runs
        for run in self.children:
            run.strip()

        self._tidy_children(index, keep_empty=True)


@dataclass
class Block(StructureUnit):
    FMT = FormatPieces('\u276e', ' ', '\u276f')
    title: Item = field(default_factory=lambda: Item())
    children: List[Item] = field(default_factory=lambda: [Item()])
    options: BlockOptions = field(default_factory=lambda: BlockOptions(method='table'))

    @classmethod
    def default_options(cls, method: str):
        """ The choice of method determines the remainder of the defaults """
        if method.startswith('att'):
            return BlockOptions(title='none', method=method,
                                style='default-attributes', title_style='default-attributes-title')
        elif method.startswith('image'):
            return BlockOptions(title='none', method=method, style='default-image')
        else:
            return BlockOptions(title='simple', method=method,
                                style='default-block', title_style='default-title')

    def column_count(self) -> int:
        """ Maximum number of runs in each block item """
        return max(len(item.children) for item in self.children) if self.children else 0

    def tidy(self, index: list) -> None:
        self.name = 'Block\u00a7' + '.'.join(str(x) for x in index)

        defaults = Block.default_options(self.options.method)
        if not self.options.style:
            self.options.style = defaults.style
        if not self.options.title_style:
            self.options.title_style = defaults.title_style
        if not self.options.title:
            self.options.title = defaults.title

        self.title.tidy(index + ['title'])
        self._tidy_children(index)

    def __hash__(self):
        return id(self)

    def __bool__(self) -> bool:
        return bool(self.children) or bool(self.title) or self.options.image > 0


@dataclass
class Section(StructureUnit):
    FMT = FormatPieces('', ' ', '')
    children: List[Block] = field(default_factory=lambda: [Block()])
    options: SectionOptions = field(default_factory=lambda: SectionOptions(style='default-section'))

    def tidy(self, index: list[int]) -> None:
        self.name = 'Section\u00a7' + '.'.join(str(x) for x in index)
        self._tidy_children(index)


@dataclass
class Sheet(StructureUnit):
    FMT = FormatPieces('', ' --- ', '')
    children: List[Section] = field(default_factory=lambda: [Section()])
    styles: Dict[str, Style] = field(default_factory=lambda: {})
    options: SheetOptions = field(default_factory=lambda: SheetOptions())
    scripts: list[list[str]] = field(default_factory=list)

    def tidy(self, index: list) -> None:
        self.name = 'Sheet'
        self._tidy_children(index)

    def blocks(self) -> Generator[Block, None, None]:
        for s in self.children:
            yield from s.children


class ElementBuilder:
    def __init__(self, modifier: str, variables: dict[str, str]):
        self.modifier = modifier
        self.variables = variables

    def from_text(self, text: str) -> list[Element]:
        pieces = self.split('({[a-z_][0-9a-z_]*})', text)
        result = []
        for is_ref, txt in pieces:
            if is_ref:
                generated = self.make_generated(txt)
                result += self.handle_widgets(generated.value, generated)
            else:
                result += self.handle_widgets(txt, None)
        return result

    def handle_widgets(self, text: str, generated: Generated or None) -> list[Element]:
        # Look for checkboxes
        pieces = self.split(r'(\[[ XOxo]])', text)
        result = []
        for is_check, txt in pieces:
            if is_check:
                value = 'X' if txt[1].lower() == 'x' else ' '
                result.append(Element(value, 'checkbox', generated))
            else:
                result += self.handle_textfield(txt, generated)
        return result

    def handle_textfield(self, text: str, generated: Generated or None) -> list[Element]:
        # Look for checkboxes
        pieces = self.split(r'(\[\[[^\]]+]])', text)
        result = []
        for is_check, txt in pieces:
            if is_check:
                value = txt[2:-2]
                result.append(Element(value, 'textfield', generated))
            else:
                result.append(Element(txt, self.modifier, generated))
        return result

    def split(self, regex: str, text: str) -> list[tuple[bool, str]]:
        parts = re.split(regex, text)
        return [(re.match(regex, p) is not None, p) for p in parts if p]

    def make_generated(self, p):
        key = p[1:-1]
        try:
            value = self.variables[key]
            return Generated(key, value)
        except KeyError:
            warnings.warn(f"Tried to use script variable '{key}' as text, but it was not defined")
            return Generated(key, '?')


def text_to_elements(base: str, modifier: Optional[str], variables: dict[str, str]) -> List[Element]:
    builder = ElementBuilder(modifier, variables)
    return builder.from_text(base)
