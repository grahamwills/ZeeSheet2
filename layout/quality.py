from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TypeVar, Generic

import common
from common import Extent, Rect

T = TypeVar("T")


class IncompatibleLayoutQualities(RuntimeError):
    pass


def _f(v) -> str:
    return common.to_str(v, places=0)


@unique
class LayoutMethod(Enum):
    WRAPPING = 1
    TABLE = 2
    COLUMNS = 3
    IMAGE = 4
    NONE = 5


@dataclass
class PlacementQuality(Generic[T]):
    """
            Contains information on the quality of a layout

            target:               What this measures the quality of. Usually a PlacedContent.
            method:               The method that was used in the layout
            count:                Number of items placed
            excess_width:         The total amount of excess width
            desired:              The desired width of the placement
            unplaced:             A count of the number of items that could not be added at all
            unplaced_descendants: A count of the number of items in children that could not be added
            bad_breaks:           Number of times we had to break within a word (a bad break)
            good_breaks:          Number of times we had to break between words (a good break)
            image_shrinkage:      Sum of factors by which images was shrunk from their desired size
            height_dev:           Average difference in heights of items in the layout from the largest

    """

    method: LayoutMethod
    count: int = 0
    excess_ss: float = None
    unplaced: int = 0
    unplaced_descendants: int = 0
    bad_breaks: int = 0
    good_breaks: int = 0
    image_shrinkage: float = 0
    height_dev: float = None

    def better(self, other: PlacementQuality):
        if other is None:
            return True
        self.check_compatible(other)

        dd = self.major_score() - other.major_score()
        if dd == 0:
            return self.minor_score() < other.minor_score()
        else:
            return dd < 0

    @property
    def excess(self):
        return self.excess_ss ** 0.5

    def _score_breaks(self) -> float:
        assert self.bad_breaks >= 0
        assert self.good_breaks >= 0
        return 10 * self.bad_breaks + self.good_breaks

    def _score_height(self) -> float:
        return self.height_dev

    def _score_excess_space(self) -> float:
        return (self.excess_ss / 100)

    def _score_image(self) -> float:
        return self.image_shrinkage * 15

    def major_score(self) -> float:
        unplaced = self.unplaced * 2 + self.unplaced_descendants
        return unplaced + self.bad_breaks / 2.5

    def minor_score(self) -> float:
        """ Score ignoring unplaced and clipped items; lower is better """

        if self.method == LayoutMethod.TABLE:
            breaks = self._score_breaks()
            excess = self._score_excess_space()
            image = self._score_image()
            return breaks + excess + image
        if self.method == LayoutMethod.COLUMNS:
            breaks = self._score_breaks()
            excess = self._score_excess_space()
            image = self._score_image()
            height = self._score_height()
            return breaks + excess + image + height
        if self.method == LayoutMethod.WRAPPING:
            breaks = self._score_breaks()
            excess = self._score_excess_space()
            return breaks + excess
        if self.method == LayoutMethod.IMAGE:
            excess = self._score_excess_space()
            image = self._score_image()
            return image + excess
        if self.method == LayoutMethod.NONE:
            return 0

    def check_compatible(self, other: PlacementQuality):
        if other is None:
            return
        if self.method != other.method:
            raise IncompatibleLayoutQualities(f'Incompatible methods: {self.method} and {other.method}')

    def str_parts(self):
        parts = []
        if self.excess_ss is not None:
            parts.append(f"excess={_f(self.excess)}")
        if self.unplaced:
            parts.append(f"unplaced={self.unplaced}")
        if self.unplaced_descendants:
            parts.append(f"unplaced_descendants={self.unplaced_descendants}")
        if self.bad_breaks or self.good_breaks:
            parts.append(f"breaks={self.bad_breaks}•{self.good_breaks}")
        if self.image_shrinkage:
            parts.append(f"image_shrink={_f(self.image_shrinkage)}")
        if self.height_dev is not None:
            parts.append(f"∆height={_f(self.height_dev)}")
        return ', '.join(parts)

    def __str__(self):
        if self.count:
            head = f"{self.method.name}({self.count})"
        else:
            head = self.method.name

        parts = self.str_parts()
        if parts:
            parts = ', ' + parts

        return '\u27e8' + head + parts + '\u27e9'

    def __bool__(self):
        raise RuntimeError('Conversion to boolean is confusing; do not call this')


def for_wrapping(excess_width: float, bad_breaks: int, good_breaks: int) -> PlacementQuality[T]:
    """ Define a quality for a text wrapping """
    return PlacementQuality(LayoutMethod.WRAPPING, count=1, excess_ss=excess_width * excess_width,
                            bad_breaks=bad_breaks, good_breaks=good_breaks)


def for_image(mode, desired: Extent, drawn: Rect, outer: Rect) -> PlacementQuality[T]:
    shrinkage = max(desired.area / drawn.area - 1, 0) if mode == 'normal' else 0
    excess = outer.area - drawn.area
    return PlacementQuality(LayoutMethod.IMAGE, count=1, excess_ss=excess, image_shrinkage=shrinkage)


_DECORATION_QUALITY = PlacementQuality(LayoutMethod.NONE)


def for_decoration() -> PlacementQuality[T]:
    """ Define a quality for anything that does not care about layout"""
    return _DECORATION_QUALITY


def for_table(cells_columnwise: list[list], unplaced: int) -> PlacementQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""

    q = PlacementQuality(LayoutMethod.TABLE, excess_ss=0, unplaced=unplaced)
    for row in cells_columnwise:
        min_excess2 = None
        for item in row:
            if item is not None:
                cell = item.quality
                if cell.method != LayoutMethod.NONE:
                    q.count += 1
                q.unplaced_descendants += cell.unplaced
                q.bad_breaks += cell.bad_breaks
                q.good_breaks += cell.good_breaks
                q.image_shrinkage += cell.image_shrinkage
                if cell.excess_ss is not None:
                    min_excess2 = min(min_excess2, cell.excess_ss) if min_excess2 is not None else cell.excess_ss
        if min_excess2:
            q.excess_ss += min_excess2

    return q


def for_columns(actual_heights: list[int], cells_columnwise: list[list], unplaced: int) -> PlacementQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""
    q = for_table(cells_columnwise, unplaced)
    q.method = LayoutMethod.COLUMNS
    # Average column difference from the maximum height column
    n = len(actual_heights)
    mid = sum(actual_heights) / n
    dev = sum((h - mid) ** 2 for h in actual_heights) / n
    q.height_dev = max(actual_heights) + dev / 10
    return q
