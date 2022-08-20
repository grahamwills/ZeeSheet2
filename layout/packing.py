from typing import Iterable, Callable

from .content import Content
from .content import PlacedContent, PlacedGroupContent
from .geom import Extent, Point, Spacing


class Packer:
    """Packs rectangular content into a given space"""

    def __init__(self,
                 items: Iterable[Content],
                 place_function: Callable[[Content, Extent], PlacedContent],
                 margin: Spacing, padding: Spacing):
        self.items = list(items)
        self.place_function = place_function
        self.margin = margin
        self.padding = padding

    def into_columns(self, width: int, ncol: int = 1) -> PlacedGroupContent:
        assert ncol == 1
        results = []
        left_inset = max(self.margin.left, self.padding.left)
        right_inset = max(self.margin.right, self.padding.right)
        available_width = width - left_inset - right_inset
        if available_width < 1:
            raise RuntimeError('Too little room to place in columns')

        last_y = 0
        last_y_with_padding = self.margin.top
        for item in self.items:
            placed = self.place_function(item, Extent(available_width, -1))
            y = max(last_y_with_padding, last_y + self.padding.top)
            placed.location = Point(left_inset, y)
            last_y = placed.bounds.bottom
            last_y_with_padding = last_y + self.padding.bottom
            results.append(placed)
        return PlacedGroupContent.from_items(results, Extent(width, -1), Extent(width, last_y + self.margin.bottom))
