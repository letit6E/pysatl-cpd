"""
Module for implementation of Aggregating Scrubber.
"""

from typing import Callable
from collections.abc import Iterable, Sequence
import numpy

from CPDShell.Core.scrubber.abstract_scrubber import Scrubber

class AggregatingScrubber(Scrubber):
    """A scrubber that creates windows based on aggregating function threshold"""
    
    def __init__(
        self,
        aggregator_func: Callable[[Sequence[float | numpy.float64]], float],
        threshold: float,
        min_window_length: int = 1,
        max_window_length: int = 100,
    ):
        super().__init__()
        self.aggregator_func = aggregator_func
        self.threshold = threshold
        self.min_window_length = min_window_length
        self.max_window_length = max_window_length
        self._window_start = 0
        self.current_window_start = 0
        self.current_window_length = 0

    def restart(self) -> None:
        """Reset scrubber state"""
        self.change_points = []
        self.is_running = True
        self._window_start = 0
        self.current_window_start = 0
        self.current_window_length = 0

    def get_windows(self) -> Iterable[Sequence[float | numpy.float64]]:
        """Generate windows based on aggregator function"""
        data_length = len(self.data)
        
        while self.is_running and self._window_start < data_length:
            window_start = self._window_start
            current_end = window_start
            window = []
            
            while current_end < data_length:
                candidate = self.data[window_start:current_end + 1]
                candidate_length = len(candidate)
                
                if candidate_length >= self.min_window_length:
                    try:
                        agg_value = self.aggregator_func(candidate)
                    except Exception as e:
                        raise ValueError(f"Aggregator function error: {str(e)}") from e
                    
                    if (agg_value >= self.threshold or 
                        candidate_length >= self.max_window_length):
                        window = candidate
                        break
                
                current_end += 1

            if window:
                self.current_window_start = window_start
                self.current_window_length = len(window)
                yield window
                self._window_start = current_end + 1
            else:
                if window_start < data_length:
                    remaining = self.data[window_start:]
                    if remaining:
                        self.current_window_start = window_start
                        self.current_window_length = len(remaining)
                        yield remaining
                break

    def add_change_points(self, window_change_points: list[int]) -> None:
        """Add change points relative to current window"""
        if self.scenario is None:
            raise ValueError("Scrubber has no associated scenario")
        
        max_cp = self.scenario.max_window_cp_number
        window_start = self.current_window_start
        
        processed_points = [
            window_start + p 
            for p in window_change_points[:max_cp] 
            if 0 <= p < self.current_window_length
        ]
        
        if self.scenario.to_localize:
            for point in processed_points:
                if point not in self.change_points:
                    self.change_points.append(point)
        else:
            self.change_points.extend(processed_points)
        
        self.change_points.sort()
