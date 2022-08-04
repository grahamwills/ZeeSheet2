from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import List, NamedTuple, Optional

ERROR_DIRECTIVE = '.. ERROR::'
WARNING_DIRECTIVE = '.. WARNING::'


class _EMPTY_CLASS:
    def has_content(self):
        return False

    def tidy(self):
        pass


_EMPTY = _EMPTY_CLASS()


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


@dataclass
class Element(StructureComponent):
    value: str
    modifier: Optional[str]

    def debug_str(self):
        if self.modifier:
            return self.value + '\u22a3' + self.modifier[:3]
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
    children: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.children.append(element)

    def debug_str(self):
        return '\u2016'.join(s.debug_str() for s in self.children)

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
    children: List[Run] = field(default_factory=lambda: [Run()])

    def debug_str(self):
        return '\ufe19'.join(s.debug_str() for s in self.children)

    def as_str(self, width: int, indent: int = 0):
        return self.children[0].as_str(width, indent=indent)

    def add_to_content(self, element: Element):
        self.children[-1].append(element)


@dataclass
class Block(StructureComponent):
    title: Run = field(default_factory=lambda: Run())
    children: List[Item] = field(default_factory=lambda: [Item()])

    def debug_str(self):
        pre = f"[{self.title.debug_str()}: " if self.title else '[ '
        return pre + ' \u2022 '.join(s.debug_str() for s in self.children) + ']'

    def add_lines_to(self, lines, width: int):
        if self.title:
            lines.append(self.title.as_str(width))
            lines.append('')
        if self.children:
            for item in self.children:
                lines.append('- ' + item.as_str(width, indent=2))
            lines.append('')

    def add_to_title(self, element: Element):
        self.title.append(element)


@dataclass
class Section(StructureComponent):
    title: Run = field(default_factory=lambda: Run())
    children: List[Block] = field(default_factory=lambda: [Block()])

    def append(self, block: Block):
        self.children.append(block)

    def debug_str(self):
        pre = f"<{self.title.debug_str()}: " if self.title else '<'
        return pre + ' '.join(s.debug_str() for s in self.children) + '>'

    def add_lines_to(self, lines, width: int):
        if self.title:
            # Since the title has to be underlined, we cannot wrap it
            title = self.title.as_str(10000)
            lines.append(title)
            lines.append('-' * len(title))
            lines.append('')
        for b in self.children:
            b.add_lines_to(lines, width)
        lines.append('')

    def add_to_title(self, element: Element):
        self.title.append(element)


@dataclass
class Sheet(StructureComponent):
    children: List[Section] = field(default_factory=lambda: [Section()])
    issues: List[Issue] = field(default_factory=list)

    def append(self, section: Section):
        self.children.append(section)

    def structure_str(self):
        return ' '.join(s.debug_str() for s in self.children)

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
            s.add_lines_to(lines, width)

        # Remove trailing section definition and blank lines
        while lines and lines[-1] == '':
            lines = lines[:-1]
        return '\n'.join(lines)
