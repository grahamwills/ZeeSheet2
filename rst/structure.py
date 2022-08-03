from dataclasses import dataclass, field
from typing import List, NamedTuple


@dataclass
class Element:
    value: str

    def __str__(self):
        return f"Element[{self.value}]"

    def structure_str(self):
        return self.value


@dataclass
class Run:
    elements: List[Element] = field(default_factory=list)

    def append(self, element: Element):
        self.elements.append(element)

    def __str__(self):
        n = len(self)
        return f"Run[{n} Elements]"

    def __len__(self):
        return len(self.elements)

    def __getitem__(self, item):
        return self.elements[item]

    def structure_str(self):
        return ' \u2022; '.join(s.structure_str() for s in self.elements) + ']'


@dataclass
class Block:
    title: str = None
    runs: List[Run] = field(default_factory=list)

    def append(self, run: Run):
        self.runs.append(run)

    def __str__(self):
        n = len(self)
        return f"Block[{n} Runs]"

    def __len__(self):
        return len(self.runs)

    def __getitem__(self, item):
        return self.runs[item]

    def structure_str(self):
        pre = f"[{self.title}: " if self.title else '[ '
        return pre + ', '.join(s.structure_str() for s in self.runs) + ']'


@dataclass
class Section:
    title: str = None
    blocks: List[Block] = field(default_factory=list)

    def append(self, block: Block):
        self.blocks.append(block)

    def __str__(self):
        n = len(self)
        return f"Section[{n} Blocks]"

    def __len__(self):
        return len(self.blocks)

    def __getitem__(self, item):
        return self.blocks[item]

    def structure_str(self):
        pre = f"<{self.title}: " if self.title else '<'
        return pre + ' '.join(s.structure_str() for s in self.blocks) + '>'


class Issue(NamedTuple):
    lineNo: int
    is_error: bool
    message: str


@dataclass
class Sheet:
    sections: List[Section] = field(default_factory=list)
    issues: List[Issue] = field(default_factory=list)

    def append(self, section: Section):
        self.sections.append(section)

    def __str__(self):
        n = len(self)
        return f"Sheet[{n} Sections]"

    def __len__(self):
        return len(self.sections)

    def __getitem__(self, item):
        return self.sections[item]

    def structure_str(self):
        return ' '.join(s.structure_str() for s in self.sections)

    def combined_issues(self):
        return ' \u2020 '.join(s.message for s in self.issues)
