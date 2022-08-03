import docutils.nodes
from .structure import *
from enum import Enum

class Target(Enum):
    SHEET = 0
    SECTION = 10
    BLOCK = 20
    BLOCK_TITLE = 21

class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)
        self.sheet = Sheet()
        self.process_stack = []

    def processing(self):
        return self.process_stack[-1]

    def start(self, what: Target):
        self.process_stack.append(what)

    def finish(self, what: Target):
        was = self.process_stack.pop()
        if was != what:
            message = f"Expected to be finishing {what}, but was processing {was}"
            raise RuntimeError(message)


    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        issue = Issue(node.line, True, f"{node.tagname} tag not supported")
        self.sheet.issues.append(issue)

    def unknown_departure(self, node: docutils.nodes.Node) -> None:
        pass

    def visit_document(self, node: docutils.nodes.Text) -> None:
        self.start(Target.SHEET)

    def depart_document(self, node: docutils.nodes.Text) -> None:
        if self.processing() == Target.SECTION:
            self.finish(Target.SECTION)
        self.finish(Target.SHEET)

    def visit_paragraph(self, node: docutils.nodes.Text) -> None:
        if self.processing() == Target.SHEET:
            # Add a default Section -- one was not defined explicitely
            self.sheet.append(Section())
            self.start(Target.SECTION)

        if self.processing() == Target.SECTION:
            self.current_section().append(Block())
            self.start(Target.BLOCK)


    def depart_paragraph(self, node: docutils.nodes.Text) -> None:
        self.finish(Target.BLOCK)


    def visit_Text(self, node: docutils.nodes.Text) -> None:
        text = node.astext().replace('\n', ' ')

        block = self.current_block()
        block.title = text



    def current_section(self) -> Section:
        return self.sheet[-1]


    def current_block(self) -> Block:
        section = self.current_section()
        return section.blocks[-1]



