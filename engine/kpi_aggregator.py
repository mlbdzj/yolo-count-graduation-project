from collections import deque
from dataclasses import dataclass, field
from typing import List


@dataclass
class KPIWindow:
    """A single 5-minute KPI window record."""
    window_start: float  # unix timestamp
    window_end: float
    working_counts: List[int] = field(default_factory=list)
    idle_counts: List[int] = field(default_factory=list)
    total_packages: int = 0


class KPIAggregator:
    """
    Aggregates frame-level stats into 5-minute windows.
    For each frame update:
      - Records working/idle counts as instantaneous snapshots
      - Increments package crossings
    Averages are computed across snapshots within each window.
    """

    def __init__(self, window_seconds: int = 300):
        self.window_seconds = window_seconds
        self._current_window: KPIWindow | None = None
        self._completed_windows: deque[KPIWindow] = deque(maxlen=100)

        # Real-time current values (latest frame)
        self.current_working = 0
        self.current_idle = 0
        self.current_packages = 0

    def update(self, working: int, idle: int, timestamp: float | None = None):
        """
        Record frame-level stats.

        Args:
            working: number of people in work zone this frame
            idle: number of people in idle zone this frame
            timestamp: unix timestamp (auto-generated if None)
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        self.current_working = working
        self.current_idle = idle

        if self._current_window is None:
            self._current_window = KPIWindow(
                window_start=timestamp,
                window_end=timestamp + self.window_seconds,
            )

        # Check if we need to roll to a new window
        if timestamp >= self._current_window.window_end:
            self._completed_windows.append(self._current_window)
            self._current_window = KPIWindow(
                window_start=self._current_window.window_end,
                window_end=self._current_window.window_end + self.window_seconds,
            )
            # Reset package counter per window
            self.current_packages = 0

        self._current_window.working_counts.append(working)
        self._current_window.idle_counts.append(idle)

    def add_package_crossing(self):
        """Increment package crossing count for the current window."""
        self.current_packages += 1
        if self._current_window is not None:
            self._current_window.total_packages += 1

    def get_current(self) -> dict:
        """Get current frame KPI snapshot."""
        return {
            "working_count": self.current_working,
            "idle_count": self.current_idle,
            "total_people": self.current_working + self.current_idle,
            "packages_unloaded": self.current_packages,
        }

    def get_window_history(self) -> list[dict]:
        """Get completed 5-minute windows as list of dicts for charting."""
        result = []
        for w in self._completed_windows:
            avg_working = (sum(w.working_counts) / len(w.working_counts)
                           if w.working_counts else 0)
            avg_idle = (sum(w.idle_counts) / len(w.idle_counts)
                        if w.idle_counts else 0)
            result.append({
                "window_start": w.window_start,
                "window_end": w.window_end,
                "avg_working": round(avg_working, 1),
                "avg_idle": round(avg_idle, 1),
                "avg_total": round(avg_working + avg_idle, 1),
                "packages_unloaded": w.total_packages,
            })
        return result

    def reset(self):
        self._current_window = None
        self._completed_windows.clear()
        self.current_working = 0
        self.current_idle = 0
        self.current_packages = 0
