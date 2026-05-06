import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ChartWidget(QWidget):
    """Real-time trend chart showing KPI over 5-minute windows."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.graph = pg.PlotWidget(title="KPI 趋势")
        self.graph.setBackground("w")
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.addLegend()

        # Curves
        self.packages_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=(33, 150, 243), width=2),
            name="包裹/5min"
        )
        self.working_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=(76, 175, 80), width=2),
            name="工作中人数(均值)"
        )
        self.idle_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=(255, 152, 0), width=2),
            name="空闲人数(均值)"
        )

        self.graph.setLabel("left", "数量")
        self.graph.setLabel("bottom", "时间窗口")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.graph)

        self._window_times: list[str] = []
        self._packages_data: list[int] = []
        self._working_data: list[float] = []
        self._idle_data: list[float] = []

    def update_from_history(self, history: list[dict]):
        """Update chart from window history."""
        if not history:
            return

        self._window_times.clear()
        self._packages_data.clear()
        self._working_data.clear()
        self._idle_data.clear()

        for w in history:
            t = time.localtime(w["window_start"])
            label = time.strftime("%H:%M", t)
            self._window_times.append(label)
            self._packages_data.append(w["packages_unloaded"])
            self._working_data.append(w["avg_working"])
            self._idle_data.append(w["avg_idle"])

        x = list(range(len(self._window_times)))
        ticks = [(i, label) for i, label in enumerate(self._window_times)]

        self.packages_curve.setData(x, self._packages_data)
        self.working_curve.setData(x, self._working_data)
        self.idle_curve.setData(x, self._idle_data)

        ax = self.graph.getAxis("bottom")
        ax.setTicks([ticks])

    def clear(self):
        self._window_times.clear()
        self._packages_data.clear()
        self._working_data.clear()
        self._idle_data.clear()
        self.packages_curve.setData([], [])
        self.working_curve.setData([], [])
        self.idle_curve.setData([], [])
