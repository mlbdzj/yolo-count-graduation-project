from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.chart_widget import ChartWidget


class KPICard(QFrame):
    """Single KPI metric card with label and value."""

    def __init__(self, title: str, color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("kpiCard")
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            KPICard {{
                background: white;
                border-radius: 8px;
                border-left: 4px solid {color};
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #666; font-size: 12px;")
        layout.addWidget(self.title_label)

        self.value_label = QLabel("--")
        self.value_label.setFont(QFont("", 24, QFont.Bold))
        self.value_label.setStyleSheet(f"color: {color};")
        layout.addWidget(self.value_label)


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
        title = QLabel("📊 实时 KPI")
        title.setFont(QFont("", 14, QFont.Bold))
        layout.addWidget(title)

        # KPI Cards in 2x2 grid
        card_grid = QGridLayout()
        card_grid.setSpacing(8)

        self.total_card = KPICard("总人数", "#2196F3")
        self.working_card = KPICard("工作中", "#4CAF50")
        self.idle_card = KPICard("空闲中", "#FF9800")
        self.packages_card = KPICard("包裹 / 5min", "#9C27B0")

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
