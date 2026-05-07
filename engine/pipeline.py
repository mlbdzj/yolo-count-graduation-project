import traceback

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from engine.detector import Detector
from engine.kpi_aggregator import KPIAggregator
from engine.tracker import Tracker
from engine.zones import ZoneManager


class VideoPipeline(QThread):
    """Video processing thread: read -> detect -> track -> zones -> aggregate."""

    frame_ready = Signal(np.ndarray)
    kpi_updated = Signal(dict)
    progress = Signal(int)  # 0-100
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        video_path: str,
        detector: Detector,
        tracker: Tracker,
        zone_manager: ZoneManager,
        kpi_aggregator: KPIAggregator,
        skip_frames: int = 2,
    ):
        super().__init__()
        self.video_path = video_path
        self.detector = detector
        self.tracker = tracker
        self.zones = zone_manager
        self.kpi = kpi_aggregator
        self.skip_frames = skip_frames
        self._running = False
        self._paused = False

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.error.emit(f"无法打开视频: {self.video_path}")
            return

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frame_interval_ms = int(1000 / fps)
        frame_idx = 0

        self._running = True
        self.zones.reset_counts()
        self.kpi.reset()

        while self._running and cap.isOpened():
            if self._paused:
                self.msleep(50)
                continue

            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1

            # Skip frames for performance
            if frame_idx % (self.skip_frames + 1) != 0:
                continue

            try:
                # 1. Detection
                dets = self.detector.detect(frame)

                # 2. Tracking
                tracked = self.tracker.update(dets)

                # 3. Zone classification & line crossing
                working = 0
                idle = 0

                if len(tracked) > 0:
                    for i in range(len(tracked)):
                        cls_id = int(tracked.class_id[i])
                        tid = int(tracked.tracker_id[i])
                        xyxy = tracked.xyxy[i]
                        cx = float((xyxy[0] + xyxy[2]) / 2)
                        cy = float((xyxy[1] + xyxy[3]) / 2)

                        if cls_id == 0:  # person
                            zone = self.zones.classify_person((cx, cy))
                            if zone == "working":
                                working += 1
                            elif zone == "idle":
                                idle += 1
                        elif cls_id == 1:  # package
                            if self.zones.check_line_cross(tid, (cx, cy)):
                                self.kpi.add_package_crossing()

                # 4. KPI update
                self.kpi.update(working, idle)

                # 5. Draw annotated frame
                annotated = self._draw_annotations(frame, tracked, working, idle)

                # 6. Emit signals
                self.frame_ready.emit(annotated)
                self.kpi_updated.emit(self.kpi.get_current())

                if total_frames > 0:
                    self.progress.emit(int(frame_idx / total_frames * 100))

            except Exception:
                traceback.print_exc()

            self.msleep(frame_interval_ms)

        cap.release()
        self._running = False
        self.finished.emit()

    def stop(self):
        self._running = False

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def _draw_annotations(self, frame: np.ndarray, tracked, working: int, idle: int) -> np.ndarray:
        """Draw detection boxes, tracker IDs, and KPI text on frame. ROI is drawn by VideoWidget overlay."""
        annotated = frame.copy()

        # Draw detections
        if len(tracked) > 0:
            for i in range(len(tracked)):
                cls_id = int(tracked.class_id[i])
                tid = int(tracked.tracker_id[i])
                xyxy = tracked.xyxy[i]

                x1, y1, x2, y2 = map(int, xyxy)

                if cls_id == 0:  # person
                    # Determine color based on zone
                    cx = (x1 + x2) / 2
                    cy = (y1 + y2) / 2
                    zone = self.zones.classify_person((cx, cy))
                    if zone == "working":
                        color = (76, 175, 80)   # green
                        label = f"P{tid} [W]"
                    elif zone == "idle":
                        color = (255, 152, 0)   # orange
                        label = f"P{tid} [I]"
                    else:
                        color = (158, 158, 158)  # grey
                        label = f"P{tid}"
                else:  # package
                    color = (33, 150, 243)  # blue
                    label = f"B{tid}"

                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                # Label background
                (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(annotated, (x1, y1 - lh - 6), (x1 + lw + 4, y1), color, -1)
                cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw KPI summary in top-left corner
        lines = [
            f"Working: {working}  Idle: {idle}  Total: {working + idle}",
            f"Packages/min: {self.kpi.current_packages}",
        ]
        y0 = 30
        for line in lines:
            (lw, lh), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(annotated, (8, y0 - lh - 6), (8 + lw + 8, y0 + 4), (0, 0, 0), -1)
            cv2.putText(annotated, line, (12, y0), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y0 += lh + 14

        return annotated
