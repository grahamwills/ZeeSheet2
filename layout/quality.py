from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, unique
from typing import TypeVar, Generic

import common

T = TypeVar("T")


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
            :param desired: The desired width of the placement
            :param actual: The actual width of the placement
            :param unplaced: A count of the number of items that could not be added at all
            :param clipped: Sum of the amount of clipped items, in characters or character-equivalents
            :param bad_breaks: Number of times we had to break within a word (a bad break)
            :param good_breaks: Number of times we had to break between words (a good break)
            :param image_shrinkage: Sum of factors by which images was shrunk from their desired size
            :param height_max: Maximum height of items in the layout
            :param height_dev: Standard deviation of heights of items in the layout

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


def for_wrapping(target: T,
                 desired: float, actual: float,
                 bad_breaks: int, good_breaks: int,
                 height: float) -> LayoutQuality[T]:
    """ Define a quality for a text wrapping"""
    return LayoutQuality(target, LayoutMethod.WRAPPING, count=1, desired=desired, actual=actual,
                         bad_breaks=bad_breaks, good_breaks=good_breaks, height_max=height, height_dev=0)


def for_image(target: T,
              desired: float, actual: float,
              desired_height: float,
              height: float) -> LayoutQuality[T]:
    """ Define a quality for an image with a desired height"""
    shrinkage = max(1.0, desired / actual, desired_height / height) - 1.0
    return LayoutQuality(target, LayoutMethod.IMAGE, count=1, desired=desired, actual=actual,
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
            if cell:
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
    q.height_dev = common.variance(actual_heights) ** 0.5
    return q
