Document structure
==================

A character sheet document has the following structure, working from the top down:

Sheet
    This is the whole document. It comprises one or more sections.
    The sheet has the same layout options as a section does, but typically the simple
    layout of of stacking sections below each other works well
Section
    A section is a rectangular area comprised of a set of blocks.
    Each section has a defined layout and places the blocks inside that layout.
    Sections usually have titles which can be displayed or hidden.
    A simple sheet may only have a single section.
Block
    The block is the fundamental layout unit. It is rectangualr area and contains a
    number of items that are laid out inside it. It has a title which may be dsiplayed or hidden.
    Blocks have the most diverse layout options, sometimes very specific to the content,
    and all the items in a block share the same basic presentation style
Item
    An item can be thought of as a piece of text, or as a row of pieces of text.
    Items can include editable fields, checkboxes and images.
    Each item is displayed as a single coherent unit.

Example
-------

For a simple character sheet consisting of a name, a picture, a description, three statistics and two skills,
we might have something like this::

    Basic Information

    - Zonani the fire mage
    - Powerfully built, she wields a staff of living flame
    - [image:nowhere.com/abc.png]

    Statistics

    - Body: **2**
    - Mind: **6**
    - Soul: **4**

    Skills

    - Oration  | +4
    - Sneaking Up On People | +3

This has one (unnamed, default) section and three blocks. The blocks have 3, 3, and 2 items in them.
The second block uses asterisks to give a strong style to the numbers, and the third block uses a vertical
bar (also knowns as a 'pipe symbol') to specify alignment.


Syntax
======

This section describes the syntax for each component


Sections
--------

A sheet starts with a default unnamed section. If you define a section before other content, it will be
replaced with that section. Sections are defined as an underlined title, like so::

    Best Section Ever
    -----------------

To start a new section, simply add a new heading, like the one above.

.. note:: You can use equal signs or a few other symbols to underline if you prefer,
          but you must be consistent; don't mix two different styles!

