from copy import copy
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Tuple, Union, Optional

from common import Extent, Point, Spacing, Rect
from common import configured_logger
from .content import PlacedContent, PlacedGroupContent, PlacementError, ItemDoesNotExistError, ExtentTooSmallError

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8

@lru_cache(maxsize=10000)
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


def items_into_buckets_combinations(item_count: int, bin_count: int, limit: int = 200) -> List[List[int]]:
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

    def column_width_possibilities(self, defined: List[float] = None, need_gaps: bool = False) -> List[List[float]]:
        # If need_gaps is true, we need to reduce available space by gaps around and between cells
        if defined is not None:
            return [defined]

        col_width = self.average_spacing.horizontal / 2
        available_space = self.bounds.width
        if need_gaps:
            available_space -= col_width * self.k

        # The total number of granularity steps we can fit in
        segment_count = int(available_space / self.granularity)
        if segment_count < self.k:
            raise ExtentTooSmallError('Too few segments to place into columns')

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

        err_a = PlacementError.aggregate(p.error for fit in a for p in fit.items)
        err_b = PlacementError.aggregate(p.error for fit in b for p in fit.items)

        if err_a.better(err_b):
            return True
        elif err_b.better(err_a):
            return False

        µ1 = sum(fit.height for fit in a) / self.k
        µ2 = sum(fit.height for fit in b) / self.k

        v1 = sum((fit.height - µ1) ** 2 for fit in a)
        v2 = sum((fit.height - µ2) ** 2 for fit in b)
        if v1 != v2:
            return v1 < v2

        return False

    def make_fits(self, widths: List[float], counts: List[int]) -> List[ColumnFit]:
        at = 0
        height = self.bounds.height
        results = []
        column_left = self.bounds.left
        for width, count in zip(widths, counts):
            fit = ColumnFit(width)
            y = self.bounds.top
            previous_margin = 0
            for i in range(at, at + count):
                if y >= height:
                    fit.clipped_items_count += 1
                else:
                    # Create the rectangle to be fitted into
                    r = Rect(column_left, column_left + width, y, height)
                    # Collapse this margin with the previous: use the larger only, don't add
                    margins = self.margins_of_item(i)
                    margins = Spacing(margins.left, margins.right, max(margins.top - previous_margin, 0),
                                      margins.bottom)
                    r = r - margins

                    if r.width < MIN_BLOCK_DIMENSION:
                        raise ExtentTooSmallError('Block cannot be placed in small area')

                    placed = self.place_item(i, r.extent)
                    placed.location = r.top_left
                    y = placed.bounds.bottom + margins.bottom
                    previous_margin = margins.bottom
                    fit.items.append(placed)
            fit.height = y
            results.append(fit)
            column_left += width
            at += count
        return results

    def place_table(self, width_allocations: List[float] = None) -> PlacedGroupContent:
        """ Expect to have the table structure methods defined and use them for placement """

        # For tables, the margins must be the same; we use the averages, but all margins should be the same
        width_choices = self.column_width_possibilities(width_allocations, need_gaps=True)

        if len(width_choices) == 0:
            LOGGER.debug(f"Fitting {self.n}\u2a2f{self.k} table using {len(width_choices)} width options")
        if len(width_choices) > 1:
            LOGGER.debug(f"Fitting {self.n}\u2a2f{self.k} table using {len(width_choices)} width options")
        else:
            LOGGER.debug(f"Fitting {self.n}\u2a2f{self.k} table using widths={width_choices[0]}")

        best = None
        for column_sizes in width_choices:
            try:
                placed_children = self._place_table(column_sizes, self.bounds)
                if placed_children.better(best):
                    best = placed_children
            except ExtentTooSmallError:
                # Skip this option
                pass
        if best is None:
            raise ExtentTooSmallError('All width choices failed to produce a good fit')
        return best

    def _place_table(self, column_sizes: List[float], bounds: Rect) -> PlacedGroupContent:
        col_gap = self.average_spacing.horizontal / 2
        row_gap = self.average_spacing.vertical / 2

        top = self.average_spacing.top
        bottom = top
        placed_items = []
        unused = copy(column_sizes)
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
                    unused[col] = min(unused[col], placed_cell.unused_space)
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
        placed_children.sum_squares_unused_space = sum(v * v for v in unused)
        return placed_children

    def place_in_columns(self, count_allocations: List[int] = None, width_allocations: List[float] = None):
        count_choices = self.column_count_possibilities(count_allocations)
        width_choices = self.column_width_possibilities(width_allocations)

        LOGGER.debug(f"Placing {self.n} items in {self.k} columns using {len(width_choices)} width options "
                     f"and {len(count_choices)} count options")

        best = None
        # Naively try all combinations
        for counts in count_choices:
            for widths in width_choices:
                try:
                    trial = self.make_fits(widths, counts)
                    if self.better(trial, best):
                        best = trial
                except ExtentTooSmallError:
                    # Just ignore failures
                    pass

        height = max(fit.height for fit in best)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in best for placed in fit.items]

        return PlacedGroupContent.from_items(all_items, extent=ext)
