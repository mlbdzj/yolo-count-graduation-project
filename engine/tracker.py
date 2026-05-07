import numpy as np
import supervision as sv
from supervision.tracker.byte_tracker.core import ByteTrack


class Tracker:
    """ByteTrack wrapper using supervision."""

    def __init__(self):
        self.byte_track = ByteTrack()

    def update(self, detections: np.ndarray) -> sv.Detections:
        """
        Update tracker with new detections.

        Args:
            detections: np.ndarray of shape (N, 6): [x1, y1, x2, y2, conf, class_id]

        Returns:
            sv.Detections enriched with tracker_id field.
        """
        if len(detections) == 0:
            return self.byte_track.update_with_detections(sv.Detections.empty())

        sv_dets = sv.Detections(
            xyxy=detections[:, :4],
            confidence=detections[:, 4],
            class_id=detections[:, 5].astype(int),
        )
        return self.byte_track.update_with_detections(sv_dets)
