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

            :param target: What this measures the quality of. Usually a PlacedContent.
            :param method:  The method that was used in the layout
            :param count: Number of items placed
            :param excess_width: The total amount of excess width
            :param desired: The desired width of the placement
            :param unplaced: A count of the number of items that could not be added at all
            :param unplaced_descendants: A count of the number of items in childrern that could not be added
            :param bad_breaks: Number of times we had to break within a word (a bad break)
            :param good_breaks: Number of times we had to break between words (a good break)
            :param image_shrinkage: Sum of factors by which images was shrunk from their desired size
            :param height_dev: Average difference in heights of items in the layout from the largest

    """

    target: T
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
        if self.unplaced != other.unplaced:
            return self.unplaced < other.unplaced
        if self.unplaced_descendants != other.unplaced_descendants:
            return self.unplaced_descendants < other.unplaced_descendants
        return self.minor_score() < other.minor_score()

    @property
    def excess(self):
        return self.excess_ss ** 0.5

    def _score_breaks(self) -> float:
        assert self.bad_breaks >= 0
        assert self.good_breaks >= 0
        return 10 * self.bad_breaks + self.good_breaks

    def _score_height(self) -> float:
        return self.height_dev / 10

    def _score_excess_space(self) -> float:
        return (self.excess_ss / 100)**0.5

    def _score_image(self) -> float:
        return self.image_shrinkage * 15

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
        name = common.name_of(self.target)
        if self.count:
            head = f"{common.name_of(name)}: {self.method.name}({self.count})"
        else:
            head = f"{common.name_of(name)}: {self.method.name}"

        parts = self.str_parts()
        if parts:
            parts = ', ' + parts

        return '\u27e8' + head + parts + '\u27e9'

    def __bool__(self):
        raise RuntimeError('Conversion to boolean is confusing; do not call this')


def for_wrapping(target: T, excess_width: float, bad_breaks: int, good_breaks: int) -> PlacementQuality[T]:
    """ Define a quality for a text wrapping """
    return PlacementQuality(target, LayoutMethod.WRAPPING, count=1, excess_ss=excess_width*excess_width,
                            bad_breaks=bad_breaks, good_breaks=good_breaks)


def for_image(target: T, mode, desired: Extent, drawn: Rect, outer: Rect) -> PlacementQuality[T]:
    shrinkage = max(desired.area / drawn.area - 1, 0) if mode == 'normal' else 0
    excess = outer.width - drawn.width
    return PlacementQuality(target, LayoutMethod.IMAGE, count=1, excess_ss=excess ** 2, image_shrinkage=shrinkage)


def for_decoration(target: T) -> PlacementQuality[T]:
    """ Define a quality for anything that does not care about layout"""
    return PlacementQuality(target, LayoutMethod.NONE)


def for_table(target: T, cells_columnwise: list[list[PlacementQuality]], unplaced: int) -> PlacementQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""

    q = PlacementQuality(target, LayoutMethod.TABLE, excess_ss=0, unplaced=unplaced)
    for row in cells_columnwise:
        min_excess2 = None
        for cell in row:
            if cell is not None:
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


def for_columns(target: T, actual_heights: list[int],
                cells_columnwise: list[list[PlacementQuality]], unplaced: int) -> PlacementQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""
    q = for_table(target, cells_columnwise, unplaced)
    q.method = LayoutMethod.COLUMNS
    q.height_dev = max(actual_heights) * len(cells_columnwise) - sum(actual_heights)
    return q
