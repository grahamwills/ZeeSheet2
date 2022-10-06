from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Tuple, Union, List

import common
import layout
from common import Extent, Spacing, Rect, configured_logger, Point, items_in_bins_combinations, items_in_bins_counts
from layout.content import ExtentTooSmallError, PlacedGroupContent, PlacedContent
from layout.optimizer import TableWidthOptimizer

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8


class ColumnOverfullError(RuntimeError):
    def __init__(self, column: int, max_items: int):
        self.column = column
        self.max_items = max_items


@dataclass
class ColumnFit:
    height: float = 0
    right_margin: float = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])

    def __str__(self):
        return f"(n={len(self.items)}, height={round(self.height)})"


class ColumnPacker:
    def __init__(self, debug_name: str, bounds: Rect, item_count: int, column_count: int, granularity: int,
                 max_width_combos: int):
        self.debug_name = debug_name
        self.n = item_count
        self.k = column_count
        self.bounds = bounds
        self.granularity = granularity
        self.max_width_combos = max_width_combos
        self.average_spacing = self._average_spacing()

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        """ Place an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def item_exists(self, item_index: Union[int, Tuple[int, int]]) -> bool:
        """ Return true if the item exists """
        raise NotImplementedError('This method must be defined by an inheriting class')

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        """ Margin of an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def span_of_item(self, item_index: Union[int, Tuple[int, int]]) -> int:
        """ The number of columns spanned by this item. Defaults to 1 """
        raise NotImplementedError('This method must be defined by an inheriting class')

    @staticmethod
    def _quality_scores(quality):
        if quality == 'low':
            granularity = 30
            max_width_combos = 8
        elif quality == 'high':
            granularity = 10
            max_width_combos = 100
        elif quality == 'extreme':
            granularity = 5
            max_width_combos = 300
        else:
            granularity = 10
            max_width_combos = 24
        return granularity, max_width_combos

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
                                   granularity: float = None) -> List[List[float]] or None:
        # If need_gaps is true, we need to reduce available space by gaps around and between cells
        if defined is not None:
            return [defined]

        granularity = granularity or self.granularity

        col_width = self.average_spacing.horizontal / 2
        available_space = self.bounds.width
        if need_gaps:
            # Padding on either side also
            available_space -= col_width * (self.k + 1)

        # The total number of granularity steps we can fit in
        segment_count = int(available_space / granularity)
        if segment_count < self.k:
            raise ExtentTooSmallError('Too few segments to place into columns')

        if items_in_bins_counts(segment_count, self.k) > self.max_width_combos:
            return None

        segment_allocations = items_in_bins_combinations(segment_count, self.k, 10000)
        results = []

        # If not going to be aded, add even division of available sapce
        if segment_count % self.k:
            results.append([available_space/self.k]*self.k)

        for i, seg_alloc in enumerate(segment_allocations):
            column_widths = [s * granularity for s in seg_alloc]
            # Add in the additional part for the extra granularity
            additional = available_space - sum(column_widths)
            column_widths[i % self.k] += additional
            results.append(column_widths)



        return results

    def _place_in_sized_columns(self, widths: list[float]) -> tuple[PlacedGroupContent, list[int]]:

        # Strategy: Fill the columns from left to right, then try moving to even out column heights
        # Start with as many as possible in the first column, then one in each other
        counts = [1] * self.k
        counts[0] = self.n - (self.k - 1)

        previous_margin = 0  # Margin required by previous column
        previous_right = self.bounds.left
        allocated = 0
        fits = []

        for c in range(0, self.k):
            count = counts[c]
            width = widths[c]
            indices = (allocated, allocated + count)
            span = (previous_right, previous_right + width)
            fit, overflow = self._place_in_single_column(indices, span, previous_margin)
            previous_margin = fit.right_margin
            fitted = len(fit.items)
            if fitted == 0:
                # Nothing went into this column -- which we cannot tolerate
                raise ExtentTooSmallError()
            if fitted < count:
                # Not everything fitted
                if c < self.k - 1:
                    # Push the unfitted ones from this column into the next column
                    counts[c + 1] += (count - fitted)
                    counts[c] = fitted
            allocated += fitted
            previous_right += width
            fits.append(fit)

        fits = self.post_placement_modifications(fits)
        result = self.fits_to_content(fits)

        # Try moving from the tallest column
        while True:
            height, idx = max(([fit.height, c] for c, fit in enumerate(fits)))

            trial_result, trial_counts = self._shuffle_down(idx, fits, widths, counts, result)
            if trial_result:
                LOGGER.debug("[{}]      ... Shuffle improvement {} -> {}: {} -> {}", self.debug_name, counts, trial_counts,
                             result.quality, trial_result.quality)
                result, counts = trial_result, trial_counts
            else:
                # No improvement
                break

        self.report(widths, counts, result)

        return result, counts

    def fits_to_content(self, fits):
        height = max(fit.height for fit in fits)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in fits for placed in fit.items]
        cell_qualities = [[cell.quality for cell in column.items] for column in fits]
        heights = [column.height for column in fits]
        unplaced_count = self.n - len(all_items)
        q = layout.quality.for_columns('Columnar', heights, cell_qualities, unplaced=unplaced_count)
        return PlacedGroupContent.from_items(all_items, q, extent=ext)

    @lru_cache
    def _place_in_single_column(self, ids: tuple[int, int], span: tuple[float, float], previous_margin_right: float):
        height = self.bounds.height
        space_is_full = False
        fit = ColumnFit(right_margin=previous_margin_right)
        y = self.bounds.top
        previous_margin_bottom = 0
        for i in range(ids[0], ids[1]):
            if y >= height:
                space_is_full = True
                break
            # Create the rectangle to be fitted into
            r = Rect(span[0], span[1], y, height)
            # Collapse this margin with the previous: use the larger only, don't add
            margins = self.margins_of_item(i)
            margins = Spacing(max(margins.left - previous_margin_right, 0), margins.right,
                              max(margins.top - previous_margin_bottom, 0), margins.bottom)
            r = r - margins

            if r.width < MIN_BLOCK_DIMENSION:
                raise ExtentTooSmallError('Block cannot be placed in small area')

            try:
                placed = self.place_item(i, r.extent)
            except ExtentTooSmallError as ex:
                # No room for this block
                space_is_full = True
                break
            placed.location = r.top_left
            y = placed.bounds.bottom + margins.bottom
            previous_margin_bottom = margins.bottom
            fit.right_margin = max(fit.right_margin, margins.right)
            fit.items.append(placed)
            if placed.quality.unplaced:
                space_is_full = True
                break
        fit.height = y
        return fit, space_is_full

    def place_table(self, width_allocations: List[float] = None) -> PlacedGroupContent:
        """ Expect to have the table structure methods defined and use them for placement """

        # For tables, the margins must be the same; we use the averages, but all margins should be the same
        granularity = self.granularity
        while True:
            width_choices = self.column_width_possibilities(width_allocations, need_gaps=True, granularity=granularity)
            if width_choices:
                break
            else:
                granularity *= 1.5

        if len(width_choices) > 1:
            LOGGER.debug("[{}] Fitting {}\u2a2f{} table using {} width options", self.debug_name, self.n, self.k,
                         len(width_choices))
        else:
            LOGGER.debug("[{}] Fitting {}\u2a2f{} table using widths={}", self.debug_name, self.n, self.k,
                         common.to_str(width_choices[0], 0))

        best = None
        best_widths = None
        for column_sizes in width_choices:
            try:
                placed_children = self.place_table_given_widths(column_sizes, self.bounds)
                if placed_children.better(best):
                    best = placed_children
                    best_widths = column_sizes
            except ExtentTooSmallError:
                # Skip this option
                pass
        if best is None:
            raise ExtentTooSmallError('All width choices failed to produce a good fit')

        if self.k > 1:
            optimizer_bounds = self.bounds
            packer = self

            class TableOptimizer(TableWidthOptimizer):
                def make_table(self, widths):
                    return packer.place_table_given_widths(list(widths), optimizer_bounds)

            adj = TableOptimizer(best_widths)
            adjusted = adj.run()
            if adjusted and adjusted.better(best):
                best = adjusted

        return best

    def place_table_given_widths(self, column_sizes: List[float], bounds: Rect) -> PlacedGroupContent:
        col_gap = self.average_spacing.horizontal / 2
        row_gap = self.average_spacing.vertical / 2

        top = self.average_spacing.top
        bottom = top
        placed_items = []
        quality_table = [[] for _ in column_sizes]
        for row in range(0, self.n):
            left = self.average_spacing.left
            max_row_height = bounds.bottom - top
            for col in range(0, self.k):
                index = (row, col)
                if self.item_exists(index):
                    column_width = column_sizes[col]
                    span = self.span_of_item(index)
                    if span == 1:
                        cell_extent = Extent(column_width, max_row_height)
                    else:
                        # Add up widths to find the correct column width (don't forget the gaps!)
                        combined = sum(i for i in column_sizes[col:col + span]) + (span - 1) * col_gap
                        cell_extent = Extent(combined, max_row_height)

                    placed_cell = self.place_item(index, cell_extent)
                    cell_quality = placed_cell.quality
                    placed_cell.location = Point(left, top)
                    bottom = max(bottom, placed_cell.bounds.bottom)
                    placed_items.append(placed_cell)
                    quality_table[col].append(cell_quality)
                else:
                    quality_table[col].append(None)

                left += cell_extent.width + col_gap
            # Update the top for the next row
            top = bottom + row_gap
        # We added an extra gap that we now remove to give the true bottom, and then add bottom margin
        table_bottom = bottom + self.average_spacing.bottom
        extent = Extent(bounds.extent.width, table_bottom)
        table_quality = layout.quality.for_table('Group', quality_table, 0)
        placed_children = PlacedGroupContent.from_items(placed_items, table_quality, extent)
        placed_children.location = bounds.top_left
        return placed_children

    def place_in_columns(self, width_allocations: List[float] = None) -> PlacedGroupContent:
        granularity = self.granularity

        # Ensure we do not have too many width options
        while True:
            width_choices = self.column_width_possibilities(width_allocations, granularity=granularity)
            if not width_choices:
                granularity *= 1.5
                LOGGER.debug("[{}] Too many width possibilities, increasing  granularity to {}",
                             self.debug_name, granularity)
            else:
                break
        LOGGER.info("[{}] Placing {} items in {} columns using {} width options",
                    self.debug_name, self.n, self.k, len(width_choices))

        best = None
        best_combo = None

        for widths in width_choices:
            try:
                trial, counts = self._place_in_sized_columns(widths)
                if trial.better(best):
                    best = trial
                    best_combo = widths, counts
                    LOGGER.debug("[{}] ... Best so far has widths={}, counts={}: unplaced={}, score={:g}",
                                self.debug_name, common.to_str(best_combo[0], 0), best_combo[1],
                                best.quality.unplaced, best.quality.minor_score())
            except ColumnOverfullError as ex:
                # Just ignore failures
                pass
            except ExtentTooSmallError:
                # Just ignore failures
                pass

        if not best:
            LOGGER.warn("[{}] No placement with widths {}", self.debug_name, common.to_str(width_choices,0))
            raise ExtentTooSmallError()
        self.report(best_combo[0], best_combo[1], best, final=True)
        LOGGER.info("[{}] Best packing has widths={}, counts={}: unplaced={}, score={:g}",
                    self.debug_name, common.to_str(best_combo[0],0), best_combo[1],
                    best.quality.unplaced, best.quality.minor_score())

        return best

    def post_placement_modifications(self, columns: list[ColumnFit]) -> list[ColumnFit]:
        # Do nothing by default
        return columns

    def report(self, widths: List[float], counts: List[int], placed: PlacedGroupContent, final: bool = False):
        # Do nothing by default
        pass

    def _shuffle_down(self, idx: int, fits: list[ColumnFit], widths: list[float], counts: list[int],
                      best: PlacedGroupContent) -> tuple[PlacedGroupContent or None, list[int] or None]:
        results = None, None

        if counts[idx] < 2:
            return results

        trial_counts = copy(counts)
        trial_fits = copy(fits)

        # Set the running markers for the columns
        previous_margin = 0 if idx == 0 else fits[idx - 1].right_margin
        previous_right = self.bounds.left + sum(widths[:idx])
        allocated = sum(counts[:idx])

        # TODO: We could probably just remove the placed item from the fit column,
        # of in ColumnFit() keep track of each item placed so we could unwind the first column and not re-place it
        # but caching may be just as good

        for target in range(idx, self.k - 1):
            # Move one item
            trial_counts[target] -= 1
            trial_counts[target + 1] += 1
            # Refit the first column
            try:
                indices = (allocated, allocated + trial_counts[target])
                span = (previous_right, previous_right + widths[target])
                fit1, overflow1 = self._place_in_single_column(indices, span, previous_margin)
                if overflow1:
                    LOGGER.error('This is weird. Placing fewer items caused overflow')
                    return results

            except (ExtentTooSmallError, ColumnOverfullError):
                LOGGER.error('This is weird. Placing fewer items caused an exception.')
                return results

            # Update running counts to be past the target column
            previous_margin = fit1.right_margin
            previous_right += widths[target]
            allocated += trial_counts[target]

            # Refit the next column
            try:
                indices = (allocated, allocated + trial_counts[target + 1])
                span = (previous_right, previous_right + widths[target + 1])
                fit2, overflow2 = self._place_in_single_column(indices, span, previous_margin)
                if overflow2:
                    # We could not shuffle any further, so we are done
                    return results
            except (ExtentTooSmallError, ColumnOverfullError):
                # We could not shuffle any further, so we are done
                return results

            # Evaluate it
            trial_fits[target] = fit1
            trial_fits[target + 1] = fit2
            trial_fits = self.post_placement_modifications(trial_fits)
            trial = self.fits_to_content(trial_fits)
            if trial.better(best):
                best = trial
                results = trial, copy(trial_counts)

        # Finished shuffling
        return results

    def __str__(self):
        return f"{self.debug_name}[n={self.n}, k={self.k}, bounds={round(self.bounds)}, " \
               f"limits={self.granularity}/{self.max_width_combos}"
