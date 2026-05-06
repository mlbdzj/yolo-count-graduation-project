import time

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ChartWidget(QWidget):
    """Real-time trend chart showing KPI over 5-minute windows."""

    # Light theme curve colors
    LIGHT_COLORS = {
        "packages": (33, 150, 243),
        "working": (76, 175, 80),
        "idle": (255, 152, 0),
    }
    # Pixel theme curve colors
    PIXEL_COLORS = {
        "packages": (0, 204, 255),
        "working": (0, 255, 65),
        "idle": (255, 136, 0),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_theme = "default"

        self.graph = pg.PlotWidget(title="KPI 趋势")
        self.graph.setBackground("w")
        self.graph.showGrid(x=True, y=True, alpha=0.3)
        self.graph.addLegend()

        c = self.LIGHT_COLORS
        self.packages_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=c["packages"], width=2),
            name="包裹/5min"
        )
        self.working_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=c["working"], width=2),
            name="工作中人数(均值)"
        )
        self.idle_curve = self.graph.plot(
            [], [], pen=pg.mkPen(color=c["idle"], width=2),
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

    def apply_theme(self, theme: str):
        self._current_theme = theme
        if theme == "pixel":
            c = self.PIXEL_COLORS
            self.graph.setBackground("#111122")
            self.graph.showGrid(x=True, y=True, alpha=0.15)

            self.packages_curve.setPen(pg.mkPen(color=c["packages"], width=3))
            self.working_curve.setPen(pg.mkPen(color=c["working"], width=3))
            self.idle_curve.setPen(pg.mkPen(color=c["idle"], width=3))

            axis_pen = pg.mkPen(color="#00ff41", width=2)
            self.graph.getAxis("left").setPen(axis_pen)
            self.graph.getAxis("bottom").setPen(axis_pen)
            self.graph.getAxis("left").setTextPen(axis_pen)
            self.graph.getAxis("bottom").setTextPen(axis_pen)
            self.graph.setLabel("left", "数量", **{"color": "#00ff41", "font-size": "12px"})
            self.graph.setLabel("bottom", "时间窗口", **{"color": "#00ff41", "font-size": "12px"})
            self.graph.setTitle(None)
        else:
            c = self.LIGHT_COLORS
            self.graph.setBackground("w")
            self.graph.showGrid(x=True, y=True, alpha=0.3)

            self.packages_curve.setPen(pg.mkPen(color=c["packages"], width=2))
            self.working_curve.setPen(pg.mkPen(color=c["working"], width=2))
            self.idle_curve.setPen(pg.mkPen(color=c["idle"], width=2))

            light_pen = pg.mkPen(color="#000000", width=1)
            self.graph.getAxis("left").setPen(light_pen)
            self.graph.getAxis("bottom").setPen(light_pen)
            self.graph.getAxis("left").setTextPen(light_pen)
            self.graph.getAxis("bottom").setTextPen(light_pen)
            self.graph.setLabel("left", "数量")
            self.graph.setLabel("bottom", "时间窗口")
            self.graph.setTitle("KPI 趋势")

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
