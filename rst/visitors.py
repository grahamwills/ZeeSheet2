from enum import Enum

import docutils.nodes

from .structure import *

class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)
        self.sheet = Sheet()
        self.process_stack = []

    def start(self, node: docutils.nodes.Node, n:int=2) -> str:
        current =  ' • '.join(self.process_stack[-n:])
        self.process_stack.append(node.tagname)
        return current

    def finish(self, node: docutils.nodes.Node):
        what = node.tagname
        was = self.process_stack.pop()
        if was != what:
            message = f"Expected to be finishing {what}, but was processing {was}"
            raise RuntimeError(message)

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        issue = Issue(node.line, True, f"{node.tagname} tag not supported")
        self.sheet.issues.append(issue)
        self.start(node)


    def unknown_departure(self, node) -> None:
        self.finish(node)

    def visit_document(self, node) -> None:
        self.start(node)

    def visit_bullet_list(self, node) -> None:
        p  = self.start(node)

    def visit_list_item(self, node) -> None:
        p = self.start(node)

    def visit_paragraph(self, node) -> None:
        self._ensure_section()
        p = self.start(node)
        if p == 'document':
            self.current_section().append(Block())
        elif p == 'bullet_list • list_item':
            pass
        else:
            raise RuntimeError("where and what")

    def visit_definition_list(self, node) -> None:
        # Ignore this -- it simply groups a set of defintion list items, which is what we care about
        self.start(node)

    def visit_definition_list_item(self, node) -> None:
        # Each item starts a block
        self._ensure_section()
        self.start(node)
        self.current_section().append(Block())

    def visit_definition(self, node) -> None:
        p = self.start(node)
        if p == 'document':
            self.current_section().append(Block())

    def visit_term(self, node) -> None:
        p = self.start(node)

    def visit_Text(self, node: docutils.nodes.Text) -> None:
        p = self.start(node)
        text = node.astext().replace('\n', ' ')
        if p == 'document • paragraph':
            self.current_block().title = text
        elif p == 'list_item • paragraph':
            run = Run()
            run.elements.append(Element(text))
            self.current_block().append(run)
        elif p == 'definition_list_item • term':
            self._ensure_block()
            self.current_block().title = text
        else:
            raise RuntimeError("Unknown sequence: " + p)


    def current_section(self) -> Section:
        return self.sheet[-1]

    def current_block(self) -> Block:
        section = self.current_section()
        return section.blocks[-1]

    def _ensure_block(self):
        self._ensure_section()
        if not self.current_section().blocks:
            self.current_section().append(Block())

    def _ensure_section(self):
        if not self.sheet.sections:
            self.sheet.append(Section())
