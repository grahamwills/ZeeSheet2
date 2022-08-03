import docutils.nodes
import docutils.nodes

from .structure import *


class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)

        # Initialize the sheet with a new section
        self.sheet = Sheet()
        self._make_new_section()

        # Set our stack of what we are processing
        self.process_stack = []

    def visit_document(self, node) -> None:
        self.start(node)

    def visit_section(self, node) -> None:
        if not self.current_section().empty():
            self._make_new_section()
        self.start(node)

    def start(self, node: docutils.nodes.Node, n: int = 2) -> str:
        current = self._current_processing(n)
        self.process_stack.append(node.tagname)
        return current

    def _current_processing(self, n: int = 2):
        current = ' • '.join(self.process_stack[-n:])
        return current

    def finish(self, node: docutils.nodes.Node):
        what = node.tagname
        was = self.process_stack.pop()
        if was != what:
            message = f"Expected to be finishing {what}, but was processing {was}"
            raise RuntimeError(message)

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        self._error(node, f"{node.tagname} tag not supported")
        self.start(node)

    def unknown_departure(self, node) -> None:
        self.finish(node)

    def visit_title(self, node) -> None:
        self.start(node)

    def visit_bullet_list(self, node) -> None:
        p = self.start(node)

    def visit_list_item(self, node) -> None:
        p = self.start(node)

    def visit_paragraph(self, node) -> None:
        p = self.start(node)
        if p == 'document' or p == 'document • section':
            self._make_new_block()
        elif p == 'bullet_list • list_item':
            pass
        else:
            self._error(node, 'Surprising paragraph ancestors')

    def visit_definition_list(self, node) -> None:
        # Ignore this -- it simply groups a set of definition list items, which is what we care about
        self.start(node)

    def visit_definition_list_item(self, node) -> None:
        # Each item starts a block
        self.start(node)
        self._make_new_block()

    def visit_definition(self, node) -> None:
        p = self.start(node)
        if p == 'document':
            self._make_new_block()

    def visit_term(self, node) -> None:
        p = self.start(node)

    def visit_Text(self, node: docutils.nodes.Text) -> None:
        p = self.start(node)
        text = node.astext().replace('\n', ' ')
        if p == 'document • paragraph' or p == 'section • paragraph':
            self.current_block().title = text
        elif p == 'list_item • paragraph':
            self._ensure_block()
            run = Run()
            run.elements.append(Element(text))
            self.current_block().append(run)
        elif p == 'definition_list_item • term':
            self._ensure_block()
            self.current_block().title = text
        elif p == 'section • title':
            self.current_section().title = text
        else:
            self._error(node, "Surprising text ancestors")

    def current_section(self) -> Section:
        return self.sheet[-1]

    def current_block(self) -> Block:
        section = self.current_section()
        return section.blocks[-1]

    def _ensure_block(self):
        if not self.current_section().blocks:
            self._make_new_block()

    def _make_new_block(self) -> None:
        self.current_section().blocks.append(Block())

    def _make_new_section(self) -> None:
         self.sheet.sections.append(Section())

    def _error(self, node: docutils.nodes.Node, message: str):
        ancestors = self._current_processing(n=5)
        text = f"{message} (processing {ancestors})"
        self.sheet.issues.append(
            Issue(node.line, True, text)
        )
