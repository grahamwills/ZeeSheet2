from __future__ import annotations

import time
from copy import Error
from typing import List, Tuple, Optional

import numpy as np
import scipy as scipy

from common import configured_logger
from .content import PlacedGroupContent

LOGGER = configured_logger(__name__)


def _score(x: List[float], adjuster: TableWidthOptimizer):
    return adjuster.score(x)


class TableWidthOptimizer:

    def __init__(self, initial_widths: List[float]):
        self.initial_widths = initial_widths
        self.total_width = sum(initial_widths)
        self.k = len(initial_widths)
        LOGGER.debug("Optimizing Table. Initial Width =" + str(initial_widths))

    def make_table(self, widths):
        raise NotImplementedError()

    def score(self, x: List[float]) -> float:
        widths = self.params_to_widths(x)
        low = min(widths)
        if low < 20:
            return 1e10
        try:
            placed = self.make_table(widths)
        except Error as ex:
            LOGGER.fine(f"{widths}: Error is '{ex}'")
            return 2e10
        score = self.placed_to_score(placed)
        LOGGER.fine(f"{widths}: Score is '{score}'")
        return score

    def placed_to_score(self, placed: PlacedGroupContent):
        # TODO: Double counted breaks?
        return 1e6 * placed.quality.bad_breaks + placed.quality.minor_score()

    def run(self) -> Optional[PlacedGroupContent]:
        x0 = np.asarray([0.5] * (self.k - 1))

        start = time.perf_counter()

        initial_simplex = self._unit_simplex()
        solution = scipy.optimize.minimize(lambda x: _score(x, self), method='Nelder-Mead', x0=x0,
                                           bounds=[(0, 1)] * (self.k - 1),
                                           options={'initial_simplex': initial_simplex, 'fatol': 25, 'xatol': 0.01})
        duration = time.perf_counter() - start

        if hasattr(solution, 'success') and not solution.success:
            LOGGER.info("Failed using nelder-mead in %1.2fs after %d evaluations: %s", duration,
                        solution.nfev, solution.message)
            return None
        else:
            widths = self.params_to_widths(solution.x)
            placed = self.make_table(widths)
            f = self.placed_to_score(placed)

            LOGGER.debug("Solved using nelder-mead in %1.2fs with %d evaluations: %s -> %s ->  %1.3f",
                         duration, solution.nfev, solution.x, widths, f)
            return placed

    def _unit_simplex(self):
        lo = 1 / 1.2 / self.k
        return [[2 / 3 if j == i else lo for j in range(self.k - 1)] for i in range(self.k)]

    def params_to_widths(self, a) -> Tuple[float]:
        pixel_diffs = (2 * a - 1) * self.total_width / self.k
        last_diff = -sum(pixel_diffs)
        return tuple(float(w + d) for w, d in zip(self.initial_widths, list(pixel_diffs) + [last_diff]))
