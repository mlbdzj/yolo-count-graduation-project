from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.chart_widget import ChartWidget


class KPICard(QFrame):
    """Single KPI metric card with label and value."""

    PIXEL_COLORS = {
        "#2196F3": "#00ccff",
        "#4CAF50": "#00ff41",
        "#FF9800": "#ff8800",
        "#9C27B0": "#cc44ff",
    }

    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.StyledPanel)
        self._color = color
        self._pixel_color = self.PIXEL_COLORS.get(color, "#00ff41")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self.title_label = QLabel(title)
        layout.addWidget(self.title_label)

        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        layout.addWidget(self.value_label)

        self.apply_theme("default")

    def apply_theme(self, theme: str):
        if theme == "pixel":
            self.setStyleSheet(f"""
                KPICard {{
                    background: #111122;
                    border: 3px solid {self._pixel_color};
                    padding: 8px;
                }}
            """)
            self.title_label.setStyleSheet("color: #00ff41; font-size: 12px;")
            self.value_label.setFont(QFont("Segoe UI", 22, QFont.Bold))
            self.value_label.setStyleSheet(f"color: {self._pixel_color};")
        else:
            self.setStyleSheet(f"""
                KPICard {{
                    background: white;
                    border-radius: 8px;
                    border-left: 4px solid {self._color};
                    padding: 8px;
                }}
            """)
            self.title_label.setStyleSheet("color: #666; font-size: 12px;")
            self.value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
            self.value_label.setStyleSheet(f"color: {self._color};")


class KPIPanel(QWidget):
    """Right-side panel showing real-time KPI cards and trend chart."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(320)
        self.setMaximumWidth(380)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Title
        self.panel_title = QLabel("实时 KPI")
        self.panel_title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(self.panel_title)

        # KPI Cards in 2x2 grid
        card_grid = QGridLayout()
        card_grid.setSpacing(8)

        self.total_card = KPICard("总人数", "#2196F3")
        self.working_card = KPICard("工作中", "#4CAF50")
        self.idle_card = KPICard("空闲中", "#FF9800")
        self.packages_card = KPICard("包裹 / min", "#9C27B0")

        card_grid.addWidget(self.total_card, 0, 0)
        card_grid.addWidget(self.working_card, 0, 1)
        card_grid.addWidget(self.idle_card, 1, 0)
        card_grid.addWidget(self.packages_card, 1, 1)
        layout.addLayout(card_grid)

        # Status label
        self.status_label = QLabel("等待视频处理...")
        self.status_label.setStyleSheet("color: #999; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: #ddd;")
        layout.addWidget(sep)

        # Chart
        self.chart = ChartWidget()
        layout.addWidget(self.chart, 1)

        # Export button
        export_layout = QHBoxLayout()
        export_layout.setContentsMargins(0, 0, 0, 0)
        self.export_btn = QPushButton("导出图表")
        self.export_btn.clicked.connect(self._export_chart)
        export_layout.addStretch()
        export_layout.addWidget(self.export_btn)
        layout.addLayout(export_layout)

        # Elapsed time
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #999; font-size: 11px;")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

    def update_kpi(self, data: dict):
        """Update KPI cards with new data."""
        self.total_card.value_label.setText(str(data.get("total_people", 0)))
        self.working_card.value_label.setText(str(data.get("working_count", 0)))
        self.idle_card.value_label.setText(str(data.get("idle_count", 0)))
        self.packages_card.value_label.setText(str(data.get("packages_unloaded", 0)))

    def set_status(self, text: str):
        self.status_label.setText(text)

    def set_time(self, text: str):
        self.time_label.setText(text)

    def _export_chart(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出图表", "kpi_chart.png",
            "PNG 图片 (*.png);;所有文件 (*.*)"
        )
        if path:
            self.chart.export_image(path)

    def apply_theme(self, theme: str):
        for card in [self.total_card, self.working_card, self.idle_card, self.packages_card]:
            card.apply_theme(theme)
        if theme == "pixel":
            self.setStyleSheet("background: #0d0d0d;")
            self.panel_title.setStyleSheet("color: #00ff41; font-size: 14px; font-weight: bold;")
            self.status_label.setStyleSheet("color: #00ff41; font-size: 11px;")
            self.time_label.setStyleSheet("color: #00ff41; font-size: 11px;")
            self.export_btn.setStyleSheet("""
                QPushButton {
                    background: #1a1a2e; color: #00ff41;
                    border: 2px solid #00ff41; padding: 6px 16px; font-size: 12px;
                }
                QPushButton:hover { background: #00ff41; color: #0d0d0d; }
            """)
        else:
            self.setStyleSheet("")
            self.panel_title.setStyleSheet("")
            self.status_label.setStyleSheet("color: #999; font-size: 11px;")
            self.time_label.setStyleSheet("color: #999; font-size: 11px;")
            self.export_btn.setStyleSheet("")
