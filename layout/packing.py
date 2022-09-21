from dataclasses import dataclass, field
from functools import lru_cache
from typing import Iterable, Callable, List, Tuple, Union, Optional

from common import Extent, Point, Spacing, Rect
from common import configured_logger
from generate.pdf import PDF
from structure import StructureUnit
from .content import PlacedContent, PlacedGroupContent, Error, ItemDoesNotExistError, ExtentTooSmallError

LOGGER = configured_logger(__name__)

@lru_cache
def bin_counts(n: int, m: int) -> int:
    # Recursion formula for the counts
    if n < m:
        return 0
    elif n == m or m == 1:
        return 1
    else:
        return bin_counts(n - 1, m - 1) + bin_counts(n - 1, m)


def _items_into_buckets_combinations(item_count: int, bin_count: int) -> List[List[int]]:
    """ Generates all possible combinations of items into buckets"""
    if bin_count == 1:
        return [[item_count]]

    results = []
    for i in range(1, item_count - bin_count + 2):
        # i items in the first, recurse to find the possibilities for the other bins
        for remainder in items_into_buckets_combinations(item_count - i, bin_count - 1):
            results.append([i] + remainder)
    return results


def items_into_buckets_combinations(item_count: int, bin_count: int, limit: int = 1500) -> List[List[int]]:
    counts = bin_counts(item_count, bin_count)
    if counts <= limit or item_count < 2 * bin_count:
        results = _items_into_buckets_combinations(item_count, bin_count)
        µ = item_count / bin_count
        return sorted(results, key=lambda array: sum((v - µ) ** 2 for v in array))
    else:
        # Try with half the number of items
        smaller = items_into_buckets_combinations(item_count // 2, bin_count, limit)
        # Scale up the values
        results = []
        if item_count % 2:
            # Add the extra number to a different bin
            for i, vals in enumerate(smaller):
                new_vals = [2 * v for v in vals]
                results.append(new_vals)
                new_vals[i % bin_count] += 1
        else:
            # Just scale up
            for vals in smaller:
                results.append([2 * v for v in vals])
        return results


@dataclass
class ColumnFit:
    width: float
    height: int = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])
    clipped_items_count: int = 0


class ColumnPacker:
    def __init__(self, bounds: Rect, item_count: int, column_count: int, granularity: int = 10):
        self.n = item_count
        self.k = column_count
        self.bounds = bounds
        self.granularity = granularity
        self.average_spacing = self._average_spacing()

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        """ Place an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        """ Margin of an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def column_count_possibilities(self, defined: List[int] = None) -> List[List[int]]:
        if defined is not None:
            return [defined]
        return items_into_buckets_combinations(self.n, self.k)

    def _average_spacing(self) -> Spacing:
        n = self.n
        left = sum(self.margins_of_item(i).left for i in range(0, n))
        right = sum(self.margins_of_item(i).right for i in range(0, n))
        top = sum(self.margins_of_item(i).top for i in range(0, n))
        bottom = sum(self.margins_of_item(i).bottom for i in range(0, n))
        return Spacing(left / n, right / n, top / n, bottom / n)

    def column_width_possibilities(self, defined: List[float] = None) -> List[List[float]]:
        if defined is not None:
            return [defined]

        col_width = self.average_spacing.horizontal / 2
        available_space = self.bounds.width - col_width * self.k

        # The total number of granularity steps we can fit in
        segment_count = int(available_space / self.granularity)
        segment_allocations = items_into_buckets_combinations(segment_count, self.k)
        results = []
        for i, seg_alloc in enumerate(segment_allocations):
            column_widths = [s * self.granularity for s in seg_alloc]
            # Add in the additional part for the extra granularity
            additional = available_space - sum(column_widths)
            column_widths[i % self.k] += additional
            results.append(column_widths)
        return results

    def better(self, a: List[ColumnFit], b: List[ColumnFit]):
        if b is None:
            return True
        clip_a = sum(fit.clipped_items_count for fit in a)
        clip_b = sum(fit.clipped_items_count for fit in b)
        if clip_a != clip_b:
            return clip_a < clip_b

        err_a = Error.aggregate(p.error for fit in a for p in fit.items)
        err_b = Error.aggregate(p.error for fit in b for p in fit.items)

        if err_a.better(err_b, ignore_unused=True):
            return True
        elif err_b.better(err_a, ignore_unused=True):
            return False

        µ1 = sum(fit.height for fit in a) / self.k
        µ2 = sum(fit.height for fit in b) / self.k

        v1 = sum((fit.height - µ1) ** 2 for fit in a)
        v2 = sum((fit.height - µ2) ** 2 for fit in b)
        if v1 != v2:
            return v1 < v2

        return err_a.unused_horizontal < err_b.unused_horizontal

    def make_fits(self, widths: List[float], counts: List[int]) -> List[ColumnFit]:
        at = 0
        height = self.bounds.height
        results = []
        for width, count in zip(widths, counts):
            fit = ColumnFit(width)
            y = self.bounds.top
            previous_margin = 0
            for i in range(at, at + count):
                if y >= height:
                    fit.clipped_items_count += 1
                else:
                    # Create the rectangle to be fitted into
                    r = Rect(self.bounds.left, self.bounds.left + width, y, height)

                    # Collapse this margin with the previous: use the larger only, don't add
                    margins = self.margins_of_item(i)
                    margins = Spacing(margins.left, margins.right, max(margins.top - previous_margin,0), margins.bottom)
                    r = r - margins
                    placed = self.place_item(i, r.extent)
                    placed.location = r.top_left
                    y = placed.bounds.bottom + margins.bottom
                    previous_margin = margins.bottom
                    fit.items.append(placed)
            fit.height = y
            results.append(fit)
        return results

    def place_table(self, width_allocations: List[float] = None):
        """ Expect to have the table structure methods defined and use them for placement """

        # For tables, the margins must be the same; we use the averages, but all margins should be the same
        width_choices = self.column_width_possibilities(width_allocations)

        best = None
        for column_sizes in width_choices:
            try:
                placed_children = self._place_table(column_sizes, self.bounds)
                LOGGER.debug(f"Placed using {column_sizes}: Error = {placed_children.error}")
                if placed_children.better(best):
                    best = placed_children
            except ExtentTooSmallError:
                # Skip this option
                pass
        return best

    def _place_table(self, column_sizes, bounds: Rect):
        col_gap = self.average_spacing.horizontal / 2
        row_gap = self.average_spacing.vertical / 2

        top = self.average_spacing.top
        bottom = top
        placed_items = []
        for row in range(0, self.n):
            left = self.average_spacing.left
            max_row_height = bounds.bottom - top
            for col in range(0, self.k):
                cell_extent = Extent(column_sizes[col], max_row_height)
                try:
                    placed_cell = self.place_item((row, col), cell_extent)
                    placed_cell.location = Point(left, top)
                    bottom = max(bottom, placed_cell.bounds.bottom)
                    placed_items.append(placed_cell)
                except ItemDoesNotExistError:
                    # Just ignore this
                    # TODO: should have cells merge nicely
                    pass
                left += cell_extent.width + col_gap
            # Update the top for the next row
            top = bottom + row_gap
        # We added an extra gap that we now remove to give the true bottom, and then add bottom margin
        table_bottom = bottom + self.average_spacing.bottom
        extent = Extent(bounds.extent.width, table_bottom)
        placed_children = PlacedGroupContent.from_items(placed_items, extent)
        placed_children.location = bounds.top_left
        return placed_children

    def place_in_columns(self, count_allocations: List[int] = None, width_allocations: List[float] = None):
        count_choices = self.column_count_possibilities(count_allocations)
        width_choices = self.column_width_possibilities(width_allocations)

        best = None

        # Naively try all combinations
        for counts in count_choices:
            for widths in width_choices:
                trial = self.make_fits(widths, counts)
                if self.better(trial, best):
                    best = trial

        height = max(fit.height for fit in best)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in best for placed in fit.items]

        return PlacedGroupContent.from_items(all_items, extent=ext)