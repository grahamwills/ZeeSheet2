from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional, Tuple, Union, List

import common
import layout
from common import Extent, Spacing, Rect, configured_logger, Point, items_in_bins_combinations, items_in_bins_counts
from layout import PlacementQuality
from layout.content import ExtentTooSmallError, PlacedGroupContent, PlacedContent

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8


@dataclass
class ColumnFit:
    height: float = 0
    right_margin: float = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])

    def __str__(self):
        return f"(n={len(self.items)}, height={round(self.height)})"


IMPROVES = 0


class ColumnPacker:
    QUALITY_TO_COMBOS = {'low': 10, 'medium': 40, 'high': 200, 'extreme': 800}

    def __init__(self, debug_name: str, bounds: Rect, item_count: int, column_count: int, max_width_combos: int):
        self.debug_name = debug_name
        self.n = item_count
        self.k = column_count
        self.bounds = bounds
        self.max_width_combos = max_width_combos
        self.average_spacing = self._average_spacing()
        self.col_gap = self.average_spacing.horizontal / 2
        self.row_gap = self.average_spacing.vertical / 2
        self.quality_table: list[list[PlacementQuality or None]] = [[None] * self.n for _ in range(0, self.k)]
        self.placed_table: list[list[PlacedContent or None]] = [[None] * self.n for _ in range(0, self.k)]
        self.column_left = [0.0] * self.k
        self.column_right = [0.0] * self.k

        # Used temporarily to make sure that we don't expand textfields when tryign to measure tables size
        self.keep_minimum_sizes = False

    def place_item(self, item_index: Union[int, Tuple[int, int]], extent: Extent) -> Optional[PlacedContent]:
        """ Place an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def margins_of_item(self, item_index: Union[int, Tuple[int, int]]) -> Optional[Spacing]:
        """ Margin of an item indexed by a list index, or table-wise by (row, count)"""
        raise NotImplementedError('This method must be defined by an inheriting class')

    def span_of_item(self, item_index: Union[int, Tuple[int, int]]) -> int:
        """ The number of columns spanned by this item. Defaults to 1 """
        raise NotImplementedError('This method must be defined by an inheriting class')

    def _average_spacing(self) -> Spacing:
        n = self.n
        left = sum(self.margins_of_item(i).left for i in range(0, n))
        right = sum(self.margins_of_item(i).right for i in range(0, n))
        top = sum(self.margins_of_item(i).top for i in range(0, n))
        bottom = sum(self.margins_of_item(i).bottom for i in range(0, n))
        return Spacing(left / n, right / n, top / n, bottom / n)

    def _place_in_sized_columns(self, widths: list[float], unplaced_limit: int
                                ) -> tuple[PlacedGroupContent or None, list[int] or None]:

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
            fit, overflow = self._place_in_one_column(indices, span, previous_margin)
            previous_margin = fit.right_margin
            fitted = len(fit.items)
            if fitted == 0:
                # Nothing went into this column -- which we cannot tolerate
                raise ExtentTooSmallError(self.debug_name, f"Items with indices={indices} did not fit into {span}")
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
        if result.quality.unplaced > unplaced_limit:
            # Does not fit well enough to continue
            return None, None

        # Try moving from the tallest column
        while True:
            height, idx = max(([fit.height, c] for c, fit in enumerate(fits)))

            trial_result, trial_counts = self._shuffle_down(idx, fits, widths, counts, result)
            if trial_result:
                LOGGER.fine("[{}]      ... Shuffle improvement {} -> {}: {} -> {}", self.debug_name, counts,
                            trial_counts,
                            result.quality, trial_result.quality)
                result, counts = trial_result, trial_counts
            else:
                # No improvement
                break
        return result, counts

    def fits_to_content(self, fits):
        height = max(fit.height for fit in fits)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in fits for placed in fit.items]
        cell_qualities = [[cell.quality for cell in column.items] for column in fits]
        heights = [column.height for column in fits]
        unplaced_count = self.n - len(all_items)
        q = layout.quality.for_columns(heights, cell_qualities, unplaced=unplaced_count)
        return PlacedGroupContent.from_items(all_items, q, extent=ext)

    @lru_cache
    def _place_in_one_column(self, ids: tuple[int, int], span: tuple[float, float], previous_margin_right: float):
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
                raise ExtentTooSmallError(self.debug_name, 'Block cannot be placed in small area')

            try:
                LOGGER.fine("[{}] Placing item {} in extent {}", self.debug_name, i, r.extent)

                placed = self.place_item(i, r.extent)
            except ExtentTooSmallError:
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

    def place_table(self, equal: bool) -> PlacedGroupContent:

        # Padding between cells and on the far left and far right
        available_space = self.bounds.width
        col_gap = self.average_spacing.horizontal / 2
        available_space -= col_gap * (self.k + 1)

        if self.k == 1:
            return self.place_table_given_widths([available_space], self.bounds)
        if equal:
            return self.place_table_given_widths([available_space / self.k] * self.k, self.bounds)

        # Multiple columns, varying widths. We need to fit automatically
        return self.fit_within_space(available_space) or self.find_best_compression()

    def fit_within_space(self, available_space):
        WID = 1e6

        per_cell_padding = (self.bounds.width - available_space) / self.k

        # Ensure we do not expand text fields to fill the area
        self.keep_minimum_sizes = True
        self.place_table_given_widths([WID] * self.k, self.bounds)
        self.keep_minimum_sizes = False
        col_width = []
        col_to_end_width = []
        expandable = []
        WID -= per_cell_padding  # Reduce the actual amount of space that was available
        for c in range(0, self.k):
            w_max = 0
            w_to_end = 0
            expand = False
            for r in range(self.n):
                item = self.placed_table[c][r]
                if item:
                    expand = expand or item.contains_expandable()
                    w = item.drawn_bounds().width + per_cell_padding
                    span = self.span_of_item((r, c))
                    if span == 1:
                        w_max = max(w_max, w)
                    elif span > 1:
                        # This must go all the way to the end
                        w_to_end = max(w_to_end, w)

            col_width.append(w_max)
            col_to_end_width.append(w_to_end)
            expandable.append(expand)
        # If necessary, increase out the size of the columns that are spanned by a single item
        # We start at column 1 because if an item spans all the columns in a table, then how we
        # divide up those columns makes no difference.
        for c in range(1, self.k):
            if col_to_end_width[c] > 0:
                available = sum(col_width[c:])
                extra_needed_per_column = (col_to_end_width[c] - available) / (self.k - c)
                if extra_needed_per_column > 0:
                    for c1 in range(c, self.k):
                        col_width[c1] += extra_needed_per_column
        total_widest = sum(col_width)

        LOGGER.fine("[{}] Widths={}, total={}", self.debug_name, col_width, total_widest)

        extra_space = available_space - total_widest
        if extra_space >= 0:
            # The columns all fit!
            n_expandable = sum(expandable)
            if n_expandable:
                # Split extra space among the columns with expandable items
                per_column = extra_space / n_expandable
                column_widths = [w + (per_column if e else 0) for w, e in zip(col_width, expandable)]
            else:
                # Split among all columns
                per_column = (extra_space) / self.k
                column_widths = [w + per_column for w in col_width]
            LOGGER.fine("[{}] Table fits: table width {} ≤ {}",
                        self.debug_name, total_widest, available_space)
            return self.place_table_given_widths(column_widths, self.bounds)
        else:
            LOGGER.fine("[{}] Table does not fit: table width {} > {}",
                        self.debug_name, total_widest, available_space)
            return None

    def find_best_compression(self) -> PlacedGroupContent:
        width_choices = self.choose_widths(need_gaps=True, equal_column_widths=False)

        if len(width_choices) > 1:
            LOGGER.fine("[{}] Fitting {}\u2a2f{} table using {} width options", self.debug_name, self.n, self.k,
                        len(width_choices))
        else:
            LOGGER.fine("[{}] Fitting {}\u2a2f{} table using widths={}", self.debug_name, self.n, self.k,
                        common.to_str(width_choices[0], 0))

        best = None
        for column_sizes in width_choices:
            try:
                placed_children = self.place_table_given_widths(column_sizes, self.bounds)
                if placed_children.better(best):
                    best = copy(placed_children)
            except ExtentTooSmallError as ex:
                LOGGER.fine(f"Could not place children with widths {common.to_str(column_sizes, 0)}: {ex}")
                pass
        if best is None:
            raise ExtentTooSmallError(self.debug_name, 'All width choices failed to produce a good fit')
        return best

    def choose_widths(self, need_gaps: bool, equal_column_widths: bool):

        available_space = self.bounds.width
        if need_gaps:
            # Padding between cells and on the far left and far right
            col_gap = self.average_spacing.horizontal / 2
            available_space -= col_gap * (self.k + 1)

        if equal_column_widths:
            # This makes it very simple
            equal = [available_space / self.k] * self.k
            return [equal]

        # Simplest possible option -- all equal
        # Find the ideal granularity -- the width 'steps' that we can use to define multiples of
        granularity = 5
        while True:
            segment_count = int(available_space / granularity)
            if segment_count < self.k:
                # Too few segments to split up; just return all cells equal width
                return [[available_space / self.k] * self.k]
            if items_in_bins_counts(segment_count, self.k) > self.max_width_combos:
                granularity += 5
            else:
                break

        segment_allocations = items_in_bins_combinations(segment_count, self.k, self.max_width_combos)
        results = []
        for i, seg_alloc in enumerate(segment_allocations):
            column_widths = [s * granularity for s in seg_alloc]
            # Add in the additional part for the extra granularity
            additional = available_space - sum(column_widths)
            column_widths[i % self.k] += additional
            results.append(column_widths)
        return results

    def place_table_given_widths(self, column_sizes: List[float], bounds: Rect) -> PlacedGroupContent:
        """ Place tabel. If no_expanding is set, do not let textfields expand to maximum size"""
        col_gap = self.col_gap
        row_gap = self.row_gap
        bottom = top = self.average_spacing.top
        placed_items = []

        lefts = self.column_left
        rights = self.column_right

        lefts[0] = self.average_spacing.left
        rights[0] = lefts[0] + column_sizes[0]
        for i in range(1, self.k):
            lefts[i] = lefts[i - 1] + column_sizes[i - 1] + col_gap
            rights[i] = lefts[i] + column_sizes[i]

        for row in range(0, self.n):
            max_row_height = bounds.bottom - top
            for col in range(0, self.k):
                index = (row, col)
                span = self.span_of_item(index)
                if span:
                    left = lefts[col]
                    right = rights[col + span - 1]
                    placed_cell = self.place_item(index, Extent(right - left, max_row_height))
                    placed_items.append(placed_cell)
                    placed_cell.location = Point(left, top)
                    bottom = max(bottom, placed_cell.bounds.bottom)
                    self.placed_table[col][row] = placed_cell
                    self.quality_table[col][row] = placed_cell.quality

            # Update the top for the next row
            top = bottom + row_gap
        # We added an extra gap that we now remove to give the true bottom, and then add bottom margin
        table_bottom = bottom + self.average_spacing.bottom
        extent = Extent(bounds.extent.width, table_bottom)
        table_quality = layout.quality.for_table(self.quality_table, 0)
        result = PlacedGroupContent.from_items(placed_items, table_quality, extent)
        result.location = bounds.top_left
        LOGGER.fine("[{}] Placed table with widths={}: Quality={}",
                    self.debug_name, column_sizes, result.quality)
        return result

    def place_in_columns(self, equal: bool = False) -> PlacedGroupContent:
        if self.n == self.k:
            # Lay out as a kx1 table instead
            self.n = 1
            return self.place_table(equal)

        width_choices = self.choose_widths(need_gaps=False, equal_column_widths=equal)

        LOGGER.info("[{}] Placing {} items in {} columns using {} width options",
                    self.debug_name, self.n, self.k, len(width_choices))

        best = None
        best_combo = None

        least_unplaced = 999999
        for widths in width_choices:
            try:
                LOGGER.fine("[{}] Attempting to place table with widths={}", self.debug_name, widths, )
                trial, counts = self._place_in_sized_columns(widths, least_unplaced)
                if trial:
                    LOGGER.fine("[{}] Placed table with widths={}: counts={}, quality={}",
                                self.debug_name, widths, counts, trial.quality)
                if trial and trial.better(best):
                    best = copy(trial)
                    least_unplaced = best.quality.unplaced
                    best_combo = widths, counts
                    LOGGER.debug("[{}] ... Best so far has widths={}, counts={}: unplaced={}, quality={}",
                                self.debug_name, common.to_str(best_combo[0], 0), best_combo[1],
                                best.quality.unplaced, best.quality )
            except ExtentTooSmallError as ex:
                LOGGER.fine(f"Could not place children with widths {common.to_str(widths, 0)}: {ex}")
                pass

        if not best:
            LOGGER.warn("[{}] No placement with widths {}", self.debug_name, common.to_str(width_choices, 0))
            raise ExtentTooSmallError(self.debug_name, f"Could not fit using {len(width_choices)} choices")
        LOGGER.info("[{}] Best packing has widths={}, counts={}: unplaced={}, score={:g}",
                    self.debug_name, common.to_str(best_combo[0], 0), best_combo[1],
                    best.quality.unplaced, best.quality.minor_score())

        return best

    def post_placement_modifications(self, columns: list[ColumnFit]) -> list[ColumnFit]:
        # Do nothing by default
        return columns

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
                fit1, overflow1 = self._place_in_one_column(indices, span, previous_margin)
                if overflow1:
                    LOGGER.error('This is weird. Placing fewer items caused overflow')
                    return results

            except ExtentTooSmallError:
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
                fit2, overflow2 = self._place_in_one_column(indices, span, previous_margin)
                if overflow2:
                    # We could not shuffle any further, so we are done
                    return results
            except ExtentTooSmallError:
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
               f"limits={self.max_width_combos}"
