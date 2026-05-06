from collections import defaultdict
from dataclasses import dataclass


@dataclass
class LineSide:
    """Represents which side of a directed line a point is on."""

    LEFT = -1  # negative cross product
    RIGHT = 1  # positive cross product
    ON = 0


def _cross_2d(a, b):
    """2D cross product: a.x * b.y - a.y * b.x"""
    return a[0] * b[1] - a[1] * b[0]


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def point_line_side(px, py, lx1, ly1, lx2, ly2):
    """
    Returns >0 if point is on the right side of the directed line,
    <0 if on the left, 0 if exactly on the line.
    Line direction: (lx1,ly1) -> (lx2,ly2)
    """
    line_vec = (lx2 - lx1, ly2 - ly1)
    point_vec = (px - lx1, py - ly1)
    return _cross_2d(line_vec, point_vec)


def point_in_polygon(px, py, polygon):
    """Ray casting algorithm. polygon is a list of (x, y) tuples."""
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


class ZoneManager:
    """
    Manages work zone, idle zone polygons and counting line.
    All coordinates are in video pixel space.
    """

    def __init__(self, work_zone_points=None, idle_zone_points=None,
                 count_line_start=None, count_line_end=None):
        self.work_zone = work_zone_points or []
        self.idle_zone = idle_zone_points or []
        self.count_line_start = count_line_start
        self.count_line_end = count_line_end

        # Track each package tracker_id's last side of the count line
        self._package_side: dict[int, int] = {}
        # Track IDs that have already been counted
        self._counted_ids: set[int] = set()

    def classify_person(self, center: tuple[float, float]) -> str:
        """
        Classify a person as 'working', 'idle', or 'unknown'
        based on which zone their center point is in.
        Work zone takes priority if point is in both.
        """
        if self.work_zone and point_in_polygon(center[0], center[1], self.work_zone):
            return "working"
        if self.idle_zone and point_in_polygon(center[0], center[1], self.idle_zone):
            return "idle"
        return "unknown"

    def check_line_cross(self, tracker_id: int, center: tuple[float, float]) -> bool:
        """Check if a package has crossed the counting line. Counts in both directions."""
        if self.count_line_start is None or self.count_line_end is None:
            return False

        side = point_line_side(
            center[0], center[1],
            self.count_line_start[0], self.count_line_start[1],
            self.count_line_end[0], self.count_line_end[1],
        )

        if abs(side) < 1e-9:
            side = 0

        if tracker_id in self._counted_ids:
            return False

        prev_side = self._package_side.get(tracker_id)

        # Count crossing when point changes from one side to the other
        if prev_side is not None and prev_side != 0 and side != 0 and prev_side * side < 0:
            self._counted_ids.add(tracker_id)
            self._package_side[tracker_id] = side
            return True

        self._package_side[tracker_id] = side
        return False

    def reset_counts(self):
        """Reset line crossing tracking for new session."""
        self._package_side.clear()
        self._counted_ids.clear()

    def to_config(self) -> dict:
        return {
            "work_zone": {
                "points": [list(p) for p in self.work_zone]
            },
            "idle_zone": {
                "points": [list(p) for p in self.idle_zone]
            },
            "count_line": {
                "start": list(self.count_line_start) if self.count_line_start else [0, 0],
                "end": list(self.count_line_end) if self.count_line_end else [0, 0],
            },
        }

    @classmethod
    def from_config(cls, config: dict):
        zones = config.get("zones", {})
        wz = zones.get("work_zone", {}).get("points", [])
        iz = zones.get("idle_zone", {}).get("points", [])
        cl = zones.get("count_line", {})
        return cls(
            work_zone_points=[tuple(p) for p in wz],
            idle_zone_points=[tuple(p) for p in iz],
            count_line_start=tuple(cl.get("start", [0, 0])) if cl else None,
            count_line_end=tuple(cl.get("end", [0, 0])) if cl else None,
        )
