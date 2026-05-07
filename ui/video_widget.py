from enum import Enum, auto

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QRubberBand, QWidget


class EditMode(Enum):
    VIEW = auto()
    DRAW_WORK_ZONE = auto()
    DRAW_IDLE_ZONE = auto()
    DRAW_COUNT_LINE = auto()


class VideoWidget(QWidget):
    """
    Video display widget with ROI editing overlay.

    Modes:
      VIEW           - normal viewing (can drag existing vertices to adjust)
      DRAW_WORK_ZONE - clicking adds vertices to work zone polygon
      DRAW_IDLE_ZONE - clicking adds vertices to idle zone polygon
      DRAW_COUNT_LINE - first click = start, second click = end of counting line
    """

    config_changed = Signal()

    ZONE_COLORS = {
        "work": QColor(76, 175, 80, 180),
        "idle": QColor(255, 152, 0, 180),
        "count_line": QColor(33, 150, 243, 220),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Theme
        self.theme: str = "default"

        # Current frame
        self._frame: np.ndarray | None = None
        self._pixmap: QPixmap | None = None

        # Coordinate transform (set on each paint)
        self._scale: float = 1.0
        self._offset_x: float = 0.0
        self._offset_y: float = 0.0
        self._scaled_w: float = 0.0
        self._scaled_h: float = 0.0

        # ROI data (in video pixel coordinates)
        self.work_zone_points: list[QPointF] = []
        self.idle_zone_points: list[QPointF] = []
        self.count_line_start: QPointF | None = None
        self.count_line_end: QPointF | None = None

        # ROI visibility
        self.show_roi: bool = True

        # Editing state
        self.edit_mode: EditMode = EditMode.VIEW
        self._current_points: list[QPointF] = []  # points being drawn (video coords)
        self._hovered_vertex: tuple[str, int] | None = None  # ("work"|"idle", index) or ("line_start",) or ("line_end",)
        self._dragging_vertex: tuple[str, int] | None = None
        self._drag_offset: QPointF = QPointF(0, 0)

    # public API

    def set_frame(self, frame: np.ndarray):
        """Set the current video frame (BGR numpy array)."""
        self._frame = frame
        self._pixmap = None  # will be regenerated in paintEvent
        self.update()

    def get_config(self) -> dict:
        """Export ROI configuration as dict for saving."""
        return {
            "zones": {
                "work_zone": {
                    "points": [[p.x(), p.y()] for p in self.work_zone_points]
                },
                "idle_zone": {
                    "points": [[p.x(), p.y()] for p in self.idle_zone_points]
                },
                "count_line": {
                    "start": [self.count_line_start.x(), self.count_line_start.y()] if self.count_line_start else [0, 0],
                    "end": [self.count_line_end.x(), self.count_line_end.y()] if self.count_line_end else [0, 0],
                },
            }
        }

    def load_config(self, config: dict):
        """Load ROI configuration from dict."""
        zones = config.get("zones", {})
        wz = zones.get("work_zone", {}).get("points", [])
        iz = zones.get("idle_zone", {}).get("points", [])
        cl = zones.get("count_line", {})

        self.work_zone_points = [QPointF(p[0], p[1]) for p in wz]
        self.idle_zone_points = [QPointF(p[0], p[1]) for p in iz]

        if cl and cl.get("start") != [0, 0]:
            self.count_line_start = QPointF(cl["start"][0], cl["start"][1])
        else:
            self.count_line_start = None

        if cl and cl.get("end") != [0, 0]:
            self.count_line_end = QPointF(cl["end"][0], cl["end"][1])
        else:
            self.count_line_end = None

        self.update()

    def set_edit_mode(self, mode: EditMode):
        """Switch editing mode."""
        self.edit_mode = mode
        self._current_points.clear()

        if mode == EditMode.DRAW_COUNT_LINE:
            self.setCursor(Qt.CrossCursor)
        elif mode in (EditMode.DRAW_WORK_ZONE, EditMode.DRAW_IDLE_ZONE):
            self.setCursor(Qt.CrossCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
            self._hovered_vertex = None

        self.update()

    def clear_work_zone(self):
        self.work_zone_points.clear()
        self.config_changed.emit()
        self.update()

    def clear_idle_zone(self):
        self.idle_zone_points.clear()
        self.config_changed.emit()
        self.update()

    def clear_count_line(self):
        self.count_line_start = None
        self.count_line_end = None
        self.config_changed.emit()
        self.update()

    # coordinate transforms

    def _compute_transform(self):
        """Compute scale and offset to fit video frame in widget."""
        if self._frame is None:
            return
        fh, fw = self._frame.shape[:2]
        wh = self.height()
        ww = self.width()
        if wh <= 0 or ww <= 0:
            return
        self._scale = min(ww / fw, wh / fh)
        self._scaled_w = fw * self._scale
        self._scaled_h = fh * self._scale
        self._offset_x = (ww - self._scaled_w) / 2
        self._offset_y = (wh - self._scaled_h) / 2

    def _video_to_widget(self, vpt: QPointF) -> QPointF:
        x = vpt.x() * self._scale + self._offset_x
        y = vpt.y() * self._scale + self._offset_y
        return QPointF(x, y)

    def _widget_to_video(self, wpt: QPointF) -> QPointF:
        x = (wpt.x() - self._offset_x) / self._scale
        y = (wpt.y() - self._offset_y) / self._scale
        return QPointF(x, y)

    # paint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background
        if self.theme == "pixel":
            painter.fillRect(self.rect(), QColor(13, 13, 13))
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 30))

        if self._frame is None:
            if self.theme == "pixel":
                painter.setPen(QColor(0, 255, 65))
                painter.setFont(QFont("Segoe UI",14))
            else:
                painter.setPen(QColor(200, 200, 200))
                painter.setFont(QFont("Segoe UI",16))
            painter.drawText(self.rect(), Qt.AlignCenter, "拖入视频文件或点击 文件→打开视频")
            return

        self._compute_transform()

        # Draw frame
        if self._pixmap is None:
            frame_rgb = self._frame[..., ::-1].copy()  # BGR -> RGB
            h, w, ch = frame_rgb.shape
            qimg = QImage(frame_rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self._pixmap = QPixmap.fromImage(qimg)

        target = QRectF(
            self._offset_x, self._offset_y,
            self._scaled_w, self._scaled_h,
        )
        painter.drawPixmap(target, self._pixmap, QRectF(0, 0, self._pixmap.width(), self._pixmap.height()))

        # Draw ROIs (only when enabled)
        if self.show_roi:
            self._draw_zone(painter, self.work_zone_points, self.ZONE_COLORS["work"], "Work Zone")
            self._draw_zone(painter, self.idle_zone_points, self.ZONE_COLORS["idle"], "Idle Zone")
            self._draw_count_line(painter)

        # Draw current in-progress drawing (always visible when editing)
        if self.edit_mode == EditMode.DRAW_WORK_ZONE:
            self._draw_polygon_preview(painter, self._current_points, self.ZONE_COLORS["work"])
        elif self.edit_mode == EditMode.DRAW_IDLE_ZONE:
            self._draw_polygon_preview(painter, self._current_points, self.ZONE_COLORS["idle"])
        elif self.edit_mode == EditMode.DRAW_COUNT_LINE:
            self._draw_line_preview(painter)

    def _draw_zone(self, painter: QPainter, points: list[QPointF], color: QColor, label: str):
        if len(points) < 3:
            return
        wpts = [self._video_to_widget(p) for p in points]

        # Fill
        path = QPainterPath()
        path.moveTo(wpts[0])
        for pt in wpts[1:]:
            path.lineTo(pt)
        path.closeSubpath()
        fill_color = QColor(color)
        fill_color.setAlpha(40)
        painter.fillPath(path, QBrush(fill_color))

        # Outline
        pen = QPen(color, 2)
        painter.setPen(pen)
        painter.drawPath(path)

        # Vertices
        painter.setBrush(QBrush(Qt.white))
        for i, pt in enumerate(wpts):
            is_hovered = self._hovered_vertex == ("work", i) or self._hovered_vertex == ("idle", i)
            if is_hovered:
                painter.setPen(QPen(Qt.yellow, 2))
                painter.setBrush(QBrush(Qt.yellow))
            else:
                painter.setPen(QPen(color.darker(120), 1))
                painter.setBrush(QBrush(Qt.white))
            painter.drawEllipse(pt, 5, 5)

        # Label at first vertex
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI",10, QFont.Bold))
        painter.drawText(wpts[0] + QPointF(8, -8), label)

    def _draw_count_line(self, painter: QPainter):
        if self.count_line_start is None or self.count_line_end is None:
            return
        ws = self._video_to_widget(self.count_line_start)
        we = self._video_to_widget(self.count_line_end)
        color = self.ZONE_COLORS["count_line"]

        # Line
        pen = QPen(color, 3)
        painter.setPen(pen)
        painter.drawLine(ws, we)

        # Arrow at end
        self._draw_arrow(painter, ws, we, color)

        # Endpoint handles
        painter.setBrush(QBrush(Qt.white))
        painter.setPen(QPen(color.darker(120), 1))

        # Start handle (greenish)
        hov_s = self._hovered_vertex == ("line_start", 0)
        if hov_s:
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(QBrush(Qt.yellow))
        painter.drawEllipse(ws, 6, 6)

        # End handle (reddish)
        hov_e = self._hovered_vertex == ("line_end", 0)
        if hov_e:
            painter.setPen(QPen(Qt.yellow, 2))
            painter.setBrush(QBrush(Qt.yellow))
        else:
            painter.setPen(QPen(QColor(244, 67, 54), 1))
        painter.drawEllipse(we, 6, 6)

        # Label
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Segoe UI",10, QFont.Bold))
        mid = (ws + we) / 2
        painter.drawText(mid + QPointF(8, -8), "Count Line")

    def _draw_arrow(self, painter: QPainter, start: QPointF, end: QPointF, color: QColor):
        """Draw arrowhead at end point."""
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1:
            return
        ux, uy = dx / length, dy / length
        arrow_len = 15
        arrow_angle = 0.45  # radians

        left = QPointF(
            end.x() - arrow_len * (ux * np.cos(arrow_angle) - uy * np.sin(arrow_angle)),
            end.y() - arrow_len * (uy * np.cos(arrow_angle) + ux * np.sin(arrow_angle)),
        )
        right = QPointF(
            end.x() - arrow_len * (ux * np.cos(-arrow_angle) - uy * np.sin(-arrow_angle)),
            end.y() - arrow_len * (uy * np.cos(-arrow_angle) + ux * np.sin(-arrow_angle)),
        )

        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        path = QPainterPath()
        path.moveTo(end)
        path.lineTo(left)
        path.lineTo(right)
        path.closeSubpath()
        painter.drawPath(path)

    def _draw_polygon_preview(self, painter: QPainter, points: list[QPointF], color: QColor):
        """Draw polygon being edited, including preview line to mouse cursor."""
        if not points:
            return

        wpts = [self._video_to_widget(p) for p in points]
        mouse_v = self._widget_to_video(self.mapFromGlobal(self.cursor().pos()))
        mouse_w = self._video_to_widget(mouse_v)

        # Lines between existing points
        pen = QPen(color, 2, Qt.DashLine)
        painter.setPen(pen)
        for i in range(len(wpts) - 1):
            painter.drawLine(wpts[i], wpts[i + 1])

        # Preview line from last point to cursor
        painter.setPen(QPen(color, 1, Qt.DotLine))
        painter.drawLine(wpts[-1], mouse_w)

        # Close preview if more than 2 points
        if len(wpts) >= 2:
            painter.drawLine(mouse_w, wpts[0])

        # Draw vertices
        painter.setBrush(QBrush(Qt.white))
        for i, pt in enumerate(wpts):
            painter.setPen(QPen(color, 1))
            painter.drawEllipse(pt, 5, 5)

        # Draw current mouse point
        painter.setPen(QPen(Qt.yellow, 1))
        painter.setBrush(QBrush(QColor(255, 255, 0, 100)))
        painter.drawEllipse(mouse_w, 4, 4)

    def _draw_line_preview(self, painter: QPainter):
        """Draw counting line being edited."""
        color = self.ZONE_COLORS["count_line"]
        mouse_v = self._widget_to_video(self.mapFromGlobal(self.cursor().pos()))
        mouse_w = self._video_to_widget(mouse_v)

        if len(self._current_points) == 0:
            # Nothing placed yet, just show cursor
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(QColor(33, 150, 243, 80)))
            painter.drawEllipse(mouse_w, 6, 6)
        elif len(self._current_points) == 1:
            # First point placed, show preview line to cursor
            w0 = self._video_to_widget(self._current_points[0])
            pen = QPen(color, 2, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(w0, mouse_w)
            # Arrow preview
            self._draw_arrow(painter, w0, mouse_w, color)
            # First point handle
            painter.setPen(QPen(color, 1))
            painter.setBrush(QBrush(Qt.white))
            painter.drawEllipse(w0, 6, 6)
            # Cursor handle
            painter.setBrush(QBrush(QColor(255, 255, 0, 100)))
            painter.drawEllipse(mouse_w, 5, 5)

    # mouse events

    def _find_vertex_at(self, wpt: QPointF, threshold: float = 8.0) -> tuple[str, int] | None:
        """Find a vertex near the given widget coordinate. Returns (group, index) or None."""
        # Check work zone vertices
        for i, pt in enumerate(self.work_zone_points):
            wp = self._video_to_widget(pt)
            if (wp - wpt).manhattanLength() < threshold:
                return ("work", i)
        # Check idle zone vertices
        for i, pt in enumerate(self.idle_zone_points):
            wp = self._video_to_widget(pt)
            if (wp - wpt).manhattanLength() < threshold:
                return ("idle", i)
        # Check count line end points
        if self.count_line_start:
            wp = self._video_to_widget(self.count_line_start)
            if (wp - wpt).manhattanLength() < threshold:
                return ("line_start", 0)
        if self.count_line_end:
            wp = self._video_to_widget(self.count_line_end)
            if (wp - wpt).manhattanLength() < threshold:
                return ("line_end", 0)
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if self._frame is None:
            return

        vpt = self._widget_to_video(event.position())

        if event.button() == Qt.RightButton:
            # Right click: complete polygon drawing
            if self.edit_mode in (EditMode.DRAW_WORK_ZONE, EditMode.DRAW_IDLE_ZONE):
                if len(self._current_points) >= 3:
                    if self.edit_mode == EditMode.DRAW_WORK_ZONE:
                        self.work_zone_points = self._current_points.copy()
                    else:
                        self.idle_zone_points = self._current_points.copy()
                    self._current_points.clear()
                    self.set_edit_mode(EditMode.VIEW)
                    self.config_changed.emit()
            elif self.edit_mode == EditMode.DRAW_COUNT_LINE:
                self._current_points.clear()
            return

        if event.button() != Qt.LeftButton:
            return

        if self.edit_mode == EditMode.VIEW:
            # In VIEW mode, check if dragging an existing vertex
            hit = self._find_vertex_at(event.position())
            if hit:
                self._dragging_vertex = hit
                self._drag_offset = event.position() - self._video_to_widget(self._get_vertex_point(hit))
                self.setCursor(Qt.ClosedHandCursor)

        elif self.edit_mode in (EditMode.DRAW_WORK_ZONE, EditMode.DRAW_IDLE_ZONE):
            self._current_points.append(vpt)
            self.update()

        elif self.edit_mode == EditMode.DRAW_COUNT_LINE:
            if len(self._current_points) == 0:
                self._current_points.append(vpt)
            elif len(self._current_points) == 1:
                self.count_line_start = self._current_points[0]
                self.count_line_end = vpt
                self._current_points.clear()
                self.set_edit_mode(EditMode.VIEW)
                self.config_changed.emit()
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._dragging_vertex:
            # Drag vertex to new position
            new_wpt = event.position() - self._drag_offset
            new_vpt = self._widget_to_video(new_wpt)
            self._set_vertex_point(self._dragging_vertex, new_vpt)
            self.update()
            return

        # Hover detection (only in VIEW mode)
        if self.edit_mode == EditMode.VIEW:
            self._hovered_vertex = self._find_vertex_at(event.position())
            if self._hovered_vertex:
                self.setCursor(Qt.OpenHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
            self.update()
        else:
            # In draw modes, redraw for preview
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._dragging_vertex:
            self._dragging_vertex = None
            self._drag_offset = QPointF(0, 0)
            self.setCursor(Qt.OpenHandCursor if self._hovered_vertex else Qt.ArrowCursor)
            self.config_changed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            if self.edit_mode != EditMode.VIEW:
                self._current_points.clear()
                self.set_edit_mode(EditMode.VIEW)
                self.update()
            return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if self.edit_mode == EditMode.VIEW and self._hovered_vertex:
                group, idx = self._hovered_vertex
                if group == "work":
                    del self.work_zone_points[idx]
                elif group == "idle":
                    del self.idle_zone_points[idx]
                elif group == "line_start":
                    self.count_line_start = None
                elif group == "line_end":
                    self.count_line_end = None
                self._hovered_vertex = None
                self.config_changed.emit()
                self.update()
            return

        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if self.edit_mode in (EditMode.DRAW_WORK_ZONE, EditMode.DRAW_IDLE_ZONE):
                if len(self._current_points) >= 3:
                    if self.edit_mode == EditMode.DRAW_WORK_ZONE:
                        self.work_zone_points = self._current_points.copy()
                    else:
                        self.idle_zone_points = self._current_points.copy()
                    self._current_points.clear()
                    self.set_edit_mode(EditMode.VIEW)
                    self.config_changed.emit()
            return

    # vertex helpers

    def _get_vertex_point(self, key: tuple[str, int]) -> QPointF:
        group, idx = key
        if group == "work":
            return self.work_zone_points[idx]
        elif group == "idle":
            return self.idle_zone_points[idx]
        elif group == "line_start":
            return self.count_line_start
        elif group == "line_end":
            return self.count_line_end
        return QPointF(0, 0)

    def _set_vertex_point(self, key: tuple[str, int], pt: QPointF):
        group, idx = key
        if group == "work":
            self.work_zone_points[idx] = pt
        elif group == "idle":
            self.idle_zone_points[idx] = pt
        elif group == "line_start":
            self.count_line_start = pt
        elif group == "line_end":
            self.count_line_end = pt
