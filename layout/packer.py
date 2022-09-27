from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional, Tuple, Union, List

from common import Extent, Spacing, Rect, configured_logger, Point, items_in_bins_combinations
from layout.content import ExtentTooSmallError, ErrorLimitExceededError, PlacedGroupContent, PlacedContent, \
    PlacementError, \
    ItemDoesNotExistError
from layout.optimizer import TableWidthOptimizer

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8


@dataclass
class ColumnFit:
    height: int = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])

    def __str__(self):
        return f"(n={len(self.items)}, height={round(self.height)})"


@dataclass
class AllColumnsFit:
    columns: List[ColumnFit]
    unplaced_count: int = 0  # Blocks that could not be placed
    tot_clipped: float = 0  # Size of partially clipped blocks
    tot_bad_breaks: int = 0  # Count of bad breaks (ones not at whitespace)

    def accumulate_error(self, error: PlacementError):
        if error is None:
            return
        self.tot_clipped += error.clipped
        self.tot_bad_breaks += error.bad_breaks

    @cached_property
    def var_heights(self) -> float:
        n = len(self.columns)
        µ = sum(c.height for c in self.columns) / n
        return sum((c.height - µ) ** 2 for c in self.columns) / n

    def better(self, other: AllColumnsFit, consider_heights: bool):
        if other is None:
            return True
        if self.unplaced_count != other.unplaced_count:
            return self.unplaced_count < other.unplaced_count
        if self.tot_clipped != other.tot_clipped:
            return self.tot_clipped < other.tot_clipped
        if self.tot_bad_breaks != other.tot_bad_breaks:
            return self.tot_bad_breaks < other.tot_bad_breaks
        if consider_heights:
            return self.var_heights < other.var_heights
        return False

    def __str__(self):
        ss = " • ".join(str(s) for s in self.columns)
        return f"AllColumnsFit[unplaced={self.unplaced_count}, clipped={self.tot_clipped}, bad_breaks=" \
               f"{self.tot_bad_breaks}: {ss}]"


class ColumnPacker:
    def __init__(self, bounds: Rect, item_count: int, column_count: int, granularity: int = None):
        self.n = item_count
        self.k = column_count
        self.bounds = bounds
        self.granularity = granularity or max(bounds.width / column_count / 2, 30)
        self.average_spacing = self._average_spacing()

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        """ Place an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        """ Margin of an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def column_count_possibilities(self, defined: list[int, ...] = None, limit: int = 100) -> list[list[int, ...]]:
        if defined is not None:
            return [defined]
        return items_in_bins_combinations(self.n, self.k, limit=limit)

    def _average_spacing(self) -> Spacing:
        n = self.n
        left = sum(self.margins_of_item(i).left for i in range(0, n))
        right = sum(self.margins_of_item(i).right for i in range(0, n))
        top = sum(self.margins_of_item(i).top for i in range(0, n))
        bottom = sum(self.margins_of_item(i).bottom for i in range(0, n))
        return Spacing(left / n, right / n, top / n, bottom / n)

    def column_width_possibilities(self,
                                   defined: List[float] = None,
                                   need_gaps: bool = False,
                                   granularity: float = None) -> List[List[float]]:
        # If need_gaps is true, we need to reduce available space by gaps around and between cells
        if defined is not None:
            return [defined]

        granularity = granularity or self.granularity

        col_width = self.average_spacing.horizontal / 2
        available_space = self.bounds.width
        if need_gaps:
            available_space -= col_width * self.k

        # The total number of granularity steps we can fit in
        segment_count = int(available_space / granularity)
        if segment_count < self.k:
            raise ExtentTooSmallError('Too few segments to place into columns')

        segment_allocations = items_in_bins_combinations(segment_count, self.k)
        results = []
        for i, seg_alloc in enumerate(segment_allocations):
            column_widths = [s * granularity for s in seg_alloc]
            # Add in the additional part for the extra granularity
            additional = available_space - sum(column_widths)
            column_widths[i % self.k] += additional
            results.append(column_widths)
        return results

    def place_in_defined_columns(self, widths: List[float], counts: List[int],
                                 best_so_far: AllColumnsFit) -> AllColumnsFit:
        at = 0
        height = self.bounds.height
        column_left = self.bounds.left

        all_fits = AllColumnsFit([ColumnFit() for _ in widths])

        previous_margin_right = 0
        next_margin_right = 0
        for width, count, fit in zip(widths, counts, all_fits.columns):
            y = self.bounds.top
            previous_margin_bottom = 0
            for i in range(at, at + count):
                if y >= height:
                    all_fits.unplaced_count += 1
                else:
                    # Create the rectangle to be fitted into
                    r = Rect(column_left, column_left + width, y, height)
                    # Collapse this margin with the previous: use the larger only, don't add
                    margins = self.margins_of_item(i)
                    margins = Spacing(max(margins.left - previous_margin_right, 0),
                                      margins.right,
                                      max(margins.top - previous_margin_bottom, 0),
                                      margins.bottom)
                    r = r - margins

                    if r.width < MIN_BLOCK_DIMENSION:
                        raise ExtentTooSmallError('Block cannot be placed in small area')

                    try:
                        placed = self.place_item(i, r.extent)
                        all_fits.accumulate_error(placed.error)

                        placed.location = r.top_left
                        y = placed.bounds.bottom + margins.bottom
                        previous_margin_bottom = margins.bottom
                        next_margin_right = max(next_margin_right, margins.right)
                        fit.items.append(placed)
                    except (ExtentTooSmallError, ItemDoesNotExistError):
                        # No room for this block
                        all_fits.unplaced_count += 1
                        continue

            if best_so_far.better(all_fits, consider_heights=False):
                raise ErrorLimitExceededError()

            fit.height = y
            column_left += width
            previous_margin_right = next_margin_right
            at += count
        return all_fits

    def place_table(self, width_allocations: List[float] = None) -> PlacedGroupContent:
        """ Expect to have the table structure methods defined and use them for placement """

        # For tables, the margins must be the same; we use the averages, but all margins should be the same
        width_choices = self.column_width_possibilities(width_allocations, need_gaps=True)

        if len(width_choices) == 0:
            LOGGER.fine(f"Fitting {self.n}\u2a2f{self.k} table using {len(width_choices)} width options")
        if len(width_choices) > 1:
            LOGGER.fine(f"Fitting {self.n}\u2a2f{self.k} table using {len(width_choices)} width options")
        else:
            LOGGER.fine(f"Fitting {self.n}\u2a2f{self.k} table using widths={width_choices[0]}")

        best = None
        best_error = PlacementError(9e99, 0, 0)
        best_widths = None
        for column_sizes in width_choices:
            try:
                placed_children = self.place_table_given_widths(column_sizes, self.bounds, best_error)
                if placed_children.better(best):
                    best = placed_children
                    best_error = best.error
                    best_widths = column_sizes
            except (ExtentTooSmallError, ErrorLimitExceededError):
                # Skip this option
                pass
        if best is None:
            raise ExtentTooSmallError('All width choices failed to produce a good fit')

        if self.k > 1:
            optimizer_bounds = self.bounds
            packer = self

            class TableOptimizer(TableWidthOptimizer):
                def make_table(self, widths):
                    return packer.place_table_given_widths(list(widths), optimizer_bounds, PlacementError(9e99, 0, 0))

            adj = TableOptimizer(best_widths)
            adjusted = adj.run()
            if adjusted and adjusted.better(best):
                best = adjusted

        return best

    def place_table_given_widths(self, column_sizes: List[float], bounds: Rect,
                                 limit_error: PlacementError) -> PlacedGroupContent:
        col_gap = self.average_spacing.horizontal / 2
        row_gap = self.average_spacing.vertical / 2

        top = self.average_spacing.top
        bottom = top
        placed_items = []
        unused = copy(column_sizes)
        accumulated_error = PlacementError(0, 0, 0)
        for row in range(0, self.n):
            left = self.average_spacing.left
            max_row_height = bounds.bottom - top
            for col in range(0, self.k):
                column_width = column_sizes[col]
                cell_extent = Extent(column_width, max_row_height)
                try:
                    placed_cell = self.place_item((row, col), cell_extent)
                    accumulated_error += placed_cell.error
                    if limit_error.better(accumulated_error):
                        raise ErrorLimitExceededError()
                    placed_cell.location = Point(left, top)
                    bottom = max(bottom, placed_cell.bounds.bottom)
                    placed_items.append(placed_cell)
                    unused[col] = min(unused[col], column_width - placed_cell.required_width)
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

    def place_in_columns(self, count_allocations: List[int] = None, width_allocations: List[float] = None,
                         limit: int = 2000):
        count_limit = limit
        granularity = self.granularity

        while True:
            count_choices = self.column_count_possibilities(count_allocations, limit=count_limit)
            width_choices = self.column_width_possibilities(width_allocations, granularity=granularity)
            n_count = len(count_choices)
            n_width = len(width_choices)
            if n_count * n_width <= limit:
                break
            if n_count > n_width:
                count_limit = min(count_limit, n_count) * 2 // 3
                LOGGER.debug(f"Too many combinations ({n_count} x {n_width}), reducing count limit to {count_limit}")
            else:
                granularity *= 1.5
                LOGGER.debug(
                    f"Too many combinations ({n_count} x {n_width}), increasing widths granularity to {granularity}")

        LOGGER.debug(f"Placing {self.n} items in {self.k} columns using {len(width_choices)} width options "
                     f"and {len(count_choices)} count options")

        best = AllColumnsFit([], unplaced_count=999999)

        # Naively try all combinations
        for counts in count_choices:
            for widths in width_choices:
                try:
                    trial = self.place_in_defined_columns(widths, counts, best_so_far=best)
                    if trial.better(best, consider_heights=True):
                        best = trial
                except (ExtentTooSmallError, ErrorLimitExceededError):
                    # Just ignore failures
                    pass
        if not best.columns:
            raise ExtentTooSmallError()

        height = max(fit.height for fit in best.columns)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in best.columns for placed in fit.items]

        return PlacedGroupContent.from_items(all_items, extent=ext)