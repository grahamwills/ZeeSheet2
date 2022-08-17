from typing import Iterable, Callable, List

from content import PlacedContent, PlacedGroupContent
from .content import Content
from .geom import Extent, Point

INF = 9e99

class Packer:
    """Packs objects into a given larger space"""

    def __init__(self, items: Iterable[Content], place_function: Callable[[Content, Extent], PlacedContent]):
        self.items = list(items)
        self.place_function = place_function

    def into_columns(self, width: int, ncol: int = 1) -> PlacedGroupContent:
        assert ncol == 1
        results = []
        extent = Extent(width, INF)
        top = 0
        for item in self.items:
            placed = self.place_function(item, extent)
            placed.location  = Point(0, top)
            top += placed.actual.height
            results.append(placed)
