import docutils.nodes
import docutils.nodes

from .structure import *

# These tags will not even be recorded
IGNORE_TAGS = {'document'}

# These tags will be recorded, but they are only used to identify where we are in the
# processing tree; no action is taken when they are entered or departed from
NO_ACTION_TAGS = {'title', 'bullet_list', 'list_item', 'definition_list', 'term'}


class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)

        # Initialize the sheet with a new empty section and block
        self.sheet = Sheet()
        self.sheet.sections.append(Section())
        self.sheet.sections[0].append(Block())

        # Set our stack of what we are processing
        self.process_stack = []

    @property
    def current_section(self) -> Section:
        """The Section we are currently defining"""
        return self.sheet.sections[-1]

    @property
    def current_block(self) -> Block:
        """The Block we are currently defining"""
        return self.sheet.sections[-1].blocks[-1]

    def unknown_visit(self, node: docutils.nodes.Node) -> None:
        """Handle a visit for node type we do not explicitly handle"""
        tag = node.tagname
        if tag in IGNORE_TAGS:
            return
        if not tag in NO_ACTION_TAGS:
            self.error(node, f"{node.tagname} tag not supported")
        self.start(node)

    def unknown_departure(self, node) -> None:
        """Handle a visit for node type we do not explicitly handle"""
        tag = node.tagname
        if tag in IGNORE_TAGS:
            return
        else:
            self.finish(node)

    # Visit methods ###################################################################

    def visit_section(self, node) -> None:
        """Unsurprisingly, each Section defines a Section"""
        self.start(node)
        self._make_new_section()

    def visit_definition_list_item(self, node) -> None:
        """Each Definition List defines a block"""
        self.start(node)
        self._make_new_block()

    def visit_definition(self, node) -> None:
        p = self.start(node)
        if p == 'document':
            self._make_new_block()

    def visit_paragraph(self, node) -> None:
        p = self.start(node)
        if p == '' or p == 'section':
            self._make_new_block()
        elif p == 'bullet_list • list_item':
            pass
        else:
            self.error(node, 'Surprising paragraph ancestors')


    def visit_Text(self, node: docutils.nodes.Text) -> None:
        p = self.start(node)
        text = node.astext().replace('\n', ' ')
        if p == 'paragraph' or p == 'section • paragraph':
            self.current_block.title = text
        elif p == 'list_item • paragraph':
            run = Run()
            run.elements.append(Element(text))
            self.current_block.append(run)
        elif p == 'definition_list_item • term':
            self.current_block.title = text
        elif p == 'section • title':
            self.current_section.title = text
        else:
            self.error(node, "Surprising text ancestors")

    # Other methods ####################################################################

    def start(self, node: docutils.nodes.Node, n: int = 2) -> str:
        current = self._processing(n)
        self.process_stack.append(node.tagname)
        return current

    def finish(self, node: docutils.nodes.Node):
        what = node.tagname
        was = self.process_stack.pop()
        if was != what:
            message = f"Expected to be finishing {what}, but was processing {was}"
            raise RuntimeError(message)

    def error(self, node: docutils.nodes.Node, message: str):
        ancestors = self._processing(n=5)
        text = f"{message} (processing {ancestors})"
        self.sheet.issues.append(
            Issue(node.line, True, text)
        )

    def _processing(self, n: int = 2):
        """Text form of where we are in the processing tree"""
        return ' • '.join(self.process_stack[-n:])

    def _make_new_section(self) -> None:
        # If the current section is undefined, we just use that
        if not self.current_section.empty():
            self.sheet.sections.append(Section())
            self.current_section.blocks.append(Block())

    def _make_new_block(self) -> None:
        # If the current block is undefined, we just use that
        if not self.current_block.empty():
            self.current_section.blocks.append(Block())
