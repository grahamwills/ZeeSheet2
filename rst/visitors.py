import docutils.nodes
import docutils.nodes

from .structure import *

# These tags will not  be recorded
IGNORE_TAGS = {'document', 'system_message', 'literal'}

# These tags will be recorded, but they are only used to identify where we are in the
# processing tree; no action is taken when they are entered or departed from
NO_ACTION_TAGS = {'title', 'bullet_list', 'list_item', 'definition_list', 'term', 'emphasis', 'strong'}

# These items as out ancestors determine that text is the title of a block
BLOCK_TITLE_ANCESTRY = {'paragraph', 'section • paragraph', 'definition_list_item • term'}


def _tag(node: docutils.nodes.Node):
    return getattr(node, 'tagname')


class StructureBuilder(docutils.nodes.NodeVisitor):
    def __init__(self, document):
        super().__init__(document)

        # Initialize the sheet with a new empty section and block
        self.sheet = Sheet()

        # Set our stack of what we are processing
        self.process_stack = []

    def tidy(self) -> Sheet:
        # Fix up pieces we added, but ended up unused
        self.sheet.tidy()
        return self.sheet


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
        tag = _tag(node)
        if tag in IGNORE_TAGS:
            return
        if tag not in NO_ACTION_TAGS:
            self.error(node, f"{tag} tag not supported")
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
        p = self.start(node, n=1)
        if p == '' or p == 'section':
            self._make_new_block()
        elif p == 'list_item':
            self._make_new_run()
        else:
            self.error(node, 'Unexpected paragraph encountered')

    def visit_system_message(self, node:docutils.nodes.system_message) -> None:
        # The departure will not be noted, so must not record this
        level = node.attributes['level']
        message = node.children[0].astext()
        if level > 2:
            self.error(node, message)
        else:
            self.warning(node, message)

        # No processing of children
        raise docutils.nodes.SkipChildren


    def visit_literal(self, node: docutils.nodes.Node) -> None:
        assert len(node.children) == 1
        text = node.children[0].astext()

        element = Element.from_text(text, 'literal')

        p = self.start(node)
        self.add_element(element, node, p)
        self.finish(node)

        # No processing of children
        raise docutils.nodes.SkipChildren


    # noinspection PyPep8Naming
    def visit_Text(self, node: docutils.nodes.Text) -> None:

        if self._parent() == 'emphasis':
            style = 'emphasis'
            p = self.start(node, skip_last=True)
        elif self._parent() == 'strong':
            style = 'strong'
            p = self.start(node, skip_last=True)
        else:
            style = None
            p = self.start(node)

        text = node.astext().replace('\n', ' ')
        element = Element.from_text(text, style)
        self.add_element(element, node, p)


    # Other methods ####################################################################

    def start(self, node: docutils.nodes.Node, n: int = 2, skip_last: bool = False) -> str:
        current = self._processing(n, skip_last=skip_last)
        self.process_stack.append(_tag(node))
        return current

    def finish(self, node: docutils.nodes.Node):
        what = _tag(node)
        expected = self.process_stack.pop()
        if expected != what:
            message = f"Expected to be finishing {expected}, but was encountered {what}"
            raise RuntimeError(message)

    def warning(self, node: docutils.nodes.Node, message: str):
        text = self._issue_description(message, node)
        self.sheet.issues.append(Issue(node.line, False, text))

    def error(self, node: docutils.nodes.Node, message: str):
        text = self._issue_description(message, node)
        self.sheet.issues.append(Issue(node.line, True, text))

    def add_element(self, element, node, p):
        if p in BLOCK_TITLE_ANCESTRY:
            self.current_block.add_to_title(element)
        elif p == 'section • title':
            self.current_section.add_to_title(element)
        elif p == 'list_item • paragraph':
            self.current_block.add_to_content(element)
        else:
            self.error(node, 'Unexpected text encountered')

    def _issue_description(self, message, node):
        ancestors = self._processing(n=5).strip()
        text = message
        if ancestors:
            text += ' (within ' + ancestors + ')'
        text = text.replace('\n', ' ')
        return text

    def _processing(self, n: int = 2, skip_last: bool = False):
        """Text form of where we are in the processing tree"""
        if skip_last:
            return ' • '.join(self.process_stack[-n - 1:-1])
        else:
            return ' • '.join(self.process_stack[-n:])

    def _parent(self):
        """Previous step in the tree"""
        return self.process_stack[-1]

    def _make_new_section(self) -> None:
        # If the current section is undefined, we just use that
        if not self.current_section.empty():
            self.sheet.sections.append(Section())

    def _make_new_block(self) -> None:
        # If the current block is undefined, we just use that
        if not self.current_block.empty():
            self.current_section.blocks.append(Block())

    def _make_new_run(self) -> None:
        # If the current run is undefined, we just use that
        block = self.current_block
        if not block.items[-1].empty():
            block.items.append(Item())
