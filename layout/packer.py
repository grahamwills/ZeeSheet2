from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Tuple, Union, List

import layout
from common import Extent, Spacing, Rect, configured_logger, Point, items_in_bins_combinations
from layout.content import ExtentTooSmallError, ErrorLimitExceededError, PlacedGroupContent, PlacedContent
from layout.optimizer import TableWidthOptimizer
from layout.quality import PlacementQuality

LOGGER = configured_logger(__name__)

MIN_BLOCK_DIMENSION = 8


class ColumnOverfullError(RuntimeError):
    def __init__(self, column: int, max_items: int):
        self.column = column
        self.max_items = max_items


@dataclass
class ColumnFit:
    height: int = 0
    items: List[PlacedContent] = field(default_factory=lambda: [])

    def __str__(self):
        return f"(n={len(self.items)}, height={round(self.height)})"


class ColumnPacker:
    def __init__(self, bounds: Rect, item_count: int, column_count: int, granularity: int = None):
        self.n = item_count
        self.k = column_count
        self.bounds = bounds

        if granularity:
            self.granularity = granularity
        else:
            self.granularity = 10 + round(2.5 * bounds.width ** 0.5, -1)
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
            # Padding on either side also
            available_space -= col_width * (self.k + 1)

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
                                 limit: Optional[PlacementQuality]) -> PlacedGroupContent:
        at = 0
        height = self.bounds.height
        column_left = self.bounds.left

        previous_margin_right = 0
        next_margin_right = 0
        columns = []
        accumulated_quality = layout.quality.PartialQuality()
        space_is_full = False
        for width, count, in zip(widths, counts):
            fit = ColumnFit()
            columns.append(fit)
            y = self.bounds.top
            previous_margin_bottom = 0
            for i in range(at, at + count):
                if y >= height:
                    space_is_full = True
                    break
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
                except ExtentTooSmallError as ex:
                    # No room for this block
                    space_is_full = True
                    break
                accumulated_quality.unplaced_descendants += placed.quality.unplaced
                accumulated_quality.clipped += placed.quality.clipped
                if accumulated_quality.worse(limit):
                    raise ErrorLimitExceededError()
                placed.location = r.top_left
                y = placed.bounds.bottom + margins.bottom
                previous_margin_bottom = margins.bottom
                next_margin_right = max(next_margin_right, margins.right)
                fit.items.append(placed)
                if placed.quality.unplaced:
                    space_is_full = True
                    break

            if space_is_full:
                if len(columns) < self.k:
                    # We ran out of space in a middle column; this is a bad count allocation
                    raise ColumnOverfullError(len(columns) - 1, len(fit.items))
                else:
                    # We did not have enough room in the final columns -- extra items will
                    # need to go to the next page
                    break

            fit.height = y
            column_left += width
            previous_margin_right = next_margin_right
            at += count

        columns = self.post_placement_modifications(columns)

        height = max(fit.height for fit in columns)
        ext = Extent(self.bounds.width, height)
        all_items = [placed for fit in columns for placed in fit.items]
        cell_qualities = [[cell.quality for cell in column.items] for column in columns]
        heights = [column.height for column in columns]
        unplaced_count = self.n - len(all_items)
        q = layout.quality.for_columns('Columnar', heights, cell_qualities, unplaced=unplaced_count)
        items = PlacedGroupContent.from_items(all_items, q, extent=ext)
        self.report(widths, counts, items)
        return items

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
        best_widths = None
        for column_sizes in width_choices:
            try:
                best_quality = best.quality if best else None
                placed_children = self.place_table_given_widths(column_sizes, self.bounds, best_quality)
                if placed_children.better(best):
                    best = placed_children
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
                    return packer.place_table_given_widths(list(widths), optimizer_bounds, None)

            adj = TableOptimizer(best_widths)
            adjusted = adj.run()
            if adjusted and adjusted.better(best):
                best = adjusted

        return best

    def place_table_given_widths(self, column_sizes: List[float], bounds: Rect,
                                 limit_quality: Optional[PlacementQuality]) -> PlacedGroupContent:
        col_gap = self.average_spacing.horizontal / 2
        row_gap = self.average_spacing.vertical / 2

        top = self.average_spacing.top
        bottom = top
        placed_items = []
        quality_table = [[] for _ in column_sizes]
        accumulated_error = layout.quality.PartialQuality()
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
                    accumulated_error.unplaced_descendants += cell_quality.unplaced
                    accumulated_error.clipped += cell_quality.clipped
                    if accumulated_error.worse(limit_quality):
                        raise ErrorLimitExceededError()
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

    def place_in_columns(self, count_allocations: List[int] = None, width_allocations: List[float] = None,
                         limit: int = 5000) -> PlacedGroupContent:
        count_limit = limit
        granularity = self.granularity

        while True:
            count_choices = self.column_count_possibilities(count_allocations, limit=count_limit)
            width_choices = self.column_width_possibilities(width_allocations, granularity=granularity)
            n_count = len(count_choices)
            n_width = len(width_choices)
            if n_count * n_width <= limit:
                break
            if n_count > 3 * n_width:
                count_limit = min(count_limit, n_count) * 2 // 3
                LOGGER.debug(f"Too many combinations ({n_count} x {n_width}), reducing count limit to {count_limit}")
            else:
                granularity *= 1.5
                LOGGER.debug(
                    f"Too many combinations ({n_count} x {n_width}), increasing widths granularity to {granularity}")

        LOGGER.info(f"Placing {self.n} items in {self.k} columns using {len(width_choices)} width options "
                    f"and {len(count_choices)} count options")

        best = None
        best_combo = None

        # Naively try all combinations
        for widths in width_choices:
            known_limits = [defaultdict(lambda: 99999) for i in range(self.k)]
            for counts in count_choices:
                # Do we know this is a bad combo?
                ok = True
                for i, c in enumerate(counts):
                    start = sum(counts[:i])
                    if c > known_limits[i][start]:
                        ok = False
                if not ok:
                    continue

                try:
                    limit = best.quality if best else None
                    trial = self.place_in_defined_columns(widths, counts, limit=limit)
                    LOGGER.fine(f"{counts} {widths}: {trial.quality}")
                    if trial.better(best):
                        best = trial
                        best_combo = widths, counts
                except ColumnOverfullError as ex:
                    start = sum(counts[:ex.column])
                    end = ex.max_items
                    known_limits[ex.column][start] = end
                except (ErrorLimitExceededError, ExtentTooSmallError):
                    # Just ignore failures
                    pass
        if not best:
            raise ExtentTooSmallError()
        self.report(best_combo[0], best_combo[1], best, True)
        return best

    def post_placement_modifications(self, columns: list[ColumnFit]) -> list[ColumnFit]:
        # Do nothing by default
        return columns

    def report(self, widths: List[float], counts: List[int], placed: PlacedGroupContent, final: bool = False):
        # Do nothing by default
        pass
