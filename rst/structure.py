from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional, ClassVar, Tuple
from collections import namedtuple
from types import SimpleNamespace

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


# Define an empty class for things with no titles
_EMPTY = SimpleNamespace(has_content = lambda : False, tidy = lambda : None)


FormatInfo = namedtuple('ClassInfo', 'open close sep')

class Issue(NamedTuple):
    lineNo: Optional[int]
    is_error: bool
    message: str

    def as_text(self) -> str:
        if self.lineNo:
            return f"[{self.lineNo:3}] {self.message}"
        else:
            return self.message


# noinspection PyUnresolvedReferences
@dataclass
class StructureComponent:
    format_pieces : ClassVar[Tuple[str,str,str]] = ('aaa', 'bbb', 'ccc')

    def __str__(self):
        return self.__class__.__name__

    def __getattr__(self, item):
        if item == 'title':
            return _EMPTY
        if item == 'children':
            return []
        raise AttributeError('Unknown attribute: ' + item)

    def __len__(self):
        return len(self.children)

    def __getitem__(self, item):
        return self.children[item]

    def last_child(self) -> StructureComponent:
        return self.children[-1]

    def has_content(self):
        return self.title_has_content() or self.children_have_content()

    def title_has_content(self):
        return self.title.has_content()

    def children_have_content(self):
        return any(s.has_content() for s in self.children)

    def tidy(self) -> None:
        self.title.tidy()
        for s in self.children:
            s.tidy()
        self.children = [s for s in self.children if s.has_content()]

    def structure_str(self):
        open, sep, close = self.format_pieces

        title = self.title.structure_str() + " ~ " if self.title_has_content() else ''
        content = sep.join(s.structure_str() for s in self.children)

        return open + (title + content).strip() + close


@dataclass
class Element(StructureComponent):
    value: str
    modifier: Optional[str]

    def structure_str(self):
        if self.modifier:
            return '\u00ab' + self.value + '\u22a3' + self.modifier[:3] + '\u00bb'
        else:
            return self.value

    def as_str(self):
        if self.modifier == 'strong':
            return '**' + self.value + '**'
        elif self.modifier == 'emphasis':
            return '*' + self.value + '*'
        elif self.modifier == 'literal':
            return '``' + self.value + '``'
        elif self.modifier is None:
            return self.value
        else:
            raise ValueError('Unknown Element modifier: ' + self.modifier)

    @classmethod
    def from_text(cls, text: str, modifier: Optional[str]):
        return cls(text, modifier)

    def is_special(self):
        return self.modifier == 'literal'

    def has_content(self):
        return True


@dataclass
class Run(StructureComponent):
    format_pieces : ClassVar[Tuple[str,str,str]] = ('', '', '')

    children: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.children.append(element)


    def structure_str(self):
        if len(self.children) == 1:
            return self.children[0].structure_str()
        else:
            return super().structure_str()

    def as_str(self, width: int, indent: int = 0) -> str:
        if not self.children:
            return ''

        splitter = re.compile(r'(\S+)')

        items = []
        for s in self.children:
            if not s.is_special():
                # Using explicit space to split keeps the whitespace around
                for w in splitter.split(s.as_str()):
                    if w != '':
                        items.append(w)
            else:
                # Do not split up anything that is not simple text
                items.append(s.as_str())

        results = []
        current_line_length = indent

        # Then try all the rest
        for this, next in zip(items, items[1:] + [' ']):
            if this == ' ':
                # a potential break point
                if current_line_length + 1 + len(next) > width:
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


@dataclass
class Item(StructureComponent):
    format_pieces : ClassVar[Tuple[str,str,str]] = ('[', ' \u2b29 ', ']')

    children: List[Run] = field(default_factory=lambda: [Run()])

    def append(self, run: Run):
        self.children.append(run)

    def as_str(self, width: int, indent: int = 0):
        assert len(self.children) == 1
        return self.children[0].as_str(width, indent=indent)

    def as_text_lines(self, width: int) -> List[str]:
        lines = []
        for idx, item in enumerate(self.children):
            if idx == 0:
                lines.append('- ' + item.as_str(width, indent=2))
            else:
                if idx == 1:
                    lines.append('')
                lines.append('  - ' + item.as_str(width, indent=4))
        return lines

    def add_to_content(self, element: Element):
        self.children[-1].append(element)


@dataclass
class Block(StructureComponent):
    format_pieces : ClassVar[Tuple[str,str,str]] = ('\u276e', ' ', '\u276f')

    title: Run = field(default_factory=lambda: Run())
    children: List[Item] = field(default_factory=lambda: [Item()])

    def as_text_lines(self, width: int) -> List[str]:
        lines = []
        if self.title:
            lines.append(self.title.as_str(width))
            lines.append('')
        if self.children:
            for item in self.children:
                lines += item.as_text_lines(width)
            lines.append('')
        return lines

    def add_to_title(self, element: Element):
        self.title.append(element)


@dataclass
class Section(StructureComponent):
    format_pieces : ClassVar[Tuple[str,str,str]] = ('', ' ', '')

    title: Run = field(default_factory=lambda: Run())
    children: List[Block] = field(default_factory=lambda: [Block()])

    def append(self, block: Block):
        self.children.append(block)

    def as_text_lines(self, width: int) -> List[str]:
        lines = []
        if self.title:
            # Since the title has to be underlined, we cannot wrap it
            title = self.title.as_str(10000)
            lines.append(title)
            lines.append('-' * len(title))
            lines.append('')
        for b in self.children:
            lines += b.as_text_lines(width)
        lines.append('')
        return lines

    def add_to_title(self, element: Element):
        self.title.append(element)


@dataclass
class Sheet(StructureComponent):
    format_pieces : ClassVar[Tuple[str,str,str]] = ('', ' --- ', '')

    children: List[Section] = field(default_factory=lambda: [Section()])
    issues: List[Issue] = field(default_factory=list)

    def append(self, section: Section):
        self.children.append(section)

    def combined_issues(self):
        return ' \u2022 '.join(s.message for s in self.issues)

    def to_text(self, width: int = 100) -> str:
        lines = []

        errors = [i for i in self.issues if i.is_error]
        warnings = [i for i in self.issues if not i.is_error]

        if errors:
            lines.append(ERROR_DIRECTIVE)
            for issue in errors:
                lines.append('   ' + issue.as_text())
            lines.append('')
        if warnings:
            lines.append(WARNING_DIRECTIVE)
            for issue in warnings:
                lines.append('   ' + issue.as_text())
            lines.append('')

        # Add lines for each section
        for s in self.children:
            lines += s.as_text_lines(width)

        # Remove trailing section definition and blank lines
        while lines and lines[-1] == '':
            lines = lines[:-1]

        return '\n'.join(lines)
