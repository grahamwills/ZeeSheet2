from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TypeVar, Generic

import common

T = TypeVar("T")


class IncompatibleLayoutQualities(RuntimeError):
    pass


def _f(v) -> str:
    return common.to_str(v, places=1)


@unique
class LayoutMethod(Enum):
    WRAPPING = 1
    TABLE = 2
    COLUMNS = 3
    IMAGE = 4
    NONE = 5


@dataclass
class LayoutQuality(Generic[T]):
    """
            Contains information on the quality of a layout

            :param target: What this measures the quality of. Usually a PlacedContent.
            :param method:  The method that was used in the layout
            :param count: Number of items placed
            :param actual: The actual width of the placement
            :param desired: The desired width of the placement
            :param unplaced: A count of the number of items that could not be added at all
            :param clipped: Sum of the amount of clipped items, in characters or character-equivalents
            :param bad_breaks: Number of times we had to break within a word (a bad break)
            :param good_breaks: Number of times we had to break between words (a good break)
            :param image_shrinkage: Sum of factors by which images was shrunk from their desired size
            :param height_max: Maximum height of items in the layout
            :param height_dev: Average difference in heights of items in the layout from the largest

    """

    target: T
    method: LayoutMethod
    count: int = 0
    desired: float = None
    actual: float = None
    unplaced: int = 0
    clipped: float = 0
    bad_breaks: int = 0
    good_breaks: int = 0
    image_shrinkage: float = 0
    height_max: float = None
    height_dev: float = None

    def strongly_better(self, other: LayoutQuality):
        """ Better is based only on unplaced and clipped items """
        if other is None:
            return True
        self.check_compatible(other)
        if self.unplaced != other.unplaced:
            return self.unplaced < other.unplaced
        return self.clipped < other.clipped

    def weakly_better(self, other: LayoutQuality):
        """ Better assuming the items have the same unplaced and clipped items """
        self.check_compatible(other)
        return self.weak_score() < other.weak_score()

    def _score_breaks(self) -> float:
        assert self.bad_breaks >= 0
        assert self.good_breaks >= 0
        return 10 * self.bad_breaks + self.good_breaks

    def _score_height(self) -> float:
        return self.height_dev / 10

    def _score_excess_space(self) -> float:
        assert self.actual <= self.desired
        v = (self.desired - self.actual) / 10
        return v * v

    def _score_image(self) -> float:
        return self.image_shrinkage * 15

    def weak_score(self) -> float:
        """ Score ignoring unplaced and clipped items; lower is better """

        '''
            count: int = 0

            unplaced: int = 0
            clipped: float = 0
            
            desired: float = None
            actual: float = None
            bad_breaks: int = 0
            good_breaks: int = 0
            image_shrinkage: float = 0
    '''
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
            return self._score_image()
        if self.method == LayoutMethod.NONE:
            return 0

    def total_items(self):
        return self.count + self.unplaced

    def check_compatible(self, other: LayoutQuality):
        if other is None:
            return
        if self.method != other.method:
            raise IncompatibleLayoutQualities(f'Incompatible methods: {self.method} and {other.method}')
        if self.total_items() != other.total_items():
            raise IncompatibleLayoutQualities(
                f'Comparing different numbers of items: {self.total_items()} and {other.total_items()}')

    def __str__(self):
        name = common.name_of(self.target)
        if self.count:
            parts = [f"{common.name_of(name)}: {self.method.name}({self.count})"]
        else:
            parts = [f"{common.name_of(name)}: {self.method.name}"]
        if self.desired is not None or self.actual is not None:
            parts.append(f"width={_f(self.actual)}•{_f(self.desired)}")
        if self.unplaced:
            parts.append(f"unplaced={self.unplaced}")
        if self.clipped:
            parts.append(f"clipped={_f(self.clipped)}")
        if self.bad_breaks or self.good_breaks:
            parts.append(f"breaks={self.bad_breaks}•{self.good_breaks}")
        if self.image_shrinkage:
            parts.append(f"image_shrink={_f(self.image_shrinkage)}")
        if self.height_max is not None or self.height_dev is not None:
            if self.count > 1:
                parts.append(f"height={_f(self.height_max)}~{_f(self.height_dev)}")
            else:
                parts.append(f"height={_f(self.height_max)}")
        return '\u27e8' + ', '.join(parts) + '\u27e9'

    def __bool__(self):
        raise RuntimeError('Conversion to boolean is confusing; do not call this')


def for_wrapping(target: T, actual: float, desired: float, clipped: int, bad_breaks: int, good_breaks: int,
                 height: float) -> LayoutQuality[T]:
    """ Define a quality for a text wrapping """
    assert actual <= desired
    return LayoutQuality(target, LayoutMethod.WRAPPING, count=1, actual=actual, desired=desired,
                         clipped=clipped, bad_breaks=bad_breaks, good_breaks=good_breaks,
                         height_max=height, height_dev=0)


def for_image(target: T, width: float, desired: float,
              height: float, desired_height: float) -> LayoutQuality[T]:
    """ Define a quality for an image with a desired height"""
    shrinkage = max((desired * desired_height) / (width * height), 1) - 1
    return LayoutQuality(target, LayoutMethod.IMAGE, count=1, actual=width, desired=desired,
                         height_max=height, height_dev=0, image_shrinkage=shrinkage)


def for_decoration(target: T) -> LayoutQuality[T]:
    """ Define a quality for anything that does not care about layout"""
    return LayoutQuality(target, LayoutMethod.NONE)


def for_table(target: T,
              column_widths: list[int],
              cells_columnwise: list[list[LayoutQuality]],
              unplaced: int
              ) -> LayoutQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""

    q = LayoutQuality(target, LayoutMethod.TABLE, desired=sum(column_widths), unplaced=unplaced)
    for row, col_width in zip(cells_columnwise, column_widths):
        col_actual_max = 0
        for cell in row:
            if cell is not None:
                if cell.method != LayoutMethod.NONE:
                    q.count += 1
                q.clipped += cell.clipped
                q.bad_breaks += cell.bad_breaks
                q.good_breaks += cell.good_breaks
                q.image_shrinkage += cell.image_shrinkage
                if cell.actual:
                    col_actual_max = max(col_actual_max, cell.actual)
        if q.actual:
            q.actual += col_actual_max
        else:
            q.actual = col_actual_max
    return q


def for_columns(target: T,
                column_widths: list[int], actual_heights: list[int],
                cells_columnwise: list[list[LayoutQuality]],
                unplaced: int
                ) -> LayoutQuality[T]:
    """ Define a quality for a table layout by aggregating the cell qualities"""

    q = for_table(target, column_widths, cells_columnwise, unplaced)
    q.method = LayoutMethod.COLUMNS
    q.height_max = max(actual_heights)
    q.height_dev = q.height_max * len(column_widths) - sum(actual_heights)
    return q
