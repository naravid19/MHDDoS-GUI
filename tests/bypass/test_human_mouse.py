# tests/bypass/test_human_mouse.py
import pytest
import math
from src.core.human_mouse import generate_bezier_path, overshoot, fitts_steps


def test_bezier_path_starts_and_ends_correctly():
    """Path must start near `start` and end near `end`."""
    pts = generate_bezier_path((0, 0), (500, 400))
    assert len(pts) >= 25, "Path must have at least 25 points (Fitts min_steps)"
    assert abs(pts[0][0] - 0) < 2 and abs(pts[0][1] - 0) < 2
    assert abs(pts[-1][0] - 500) < 2 and abs(pts[-1][1] - 400) < 2


def test_bezier_path_not_straight_line():
    """Bezier curve should deviate from straight line between two points."""
    pts = generate_bezier_path((0, 0), (1000, 0))
    y_values = [p[1] for p in pts[1:-1]]
    assert any(abs(y) > 0.5 for y in y_values), "Bezier must curve, not go straight"


def test_bezier_path_all_positive():
    """All generated points must be non-negative (can't move off screen)."""
    pts = generate_bezier_path((50, 50), (800, 600))
    assert all(p[0] >= 0 and p[1] >= 0 for p in pts)


def test_overshoot_within_radius():
    """Overshoot point must be within `radius` distance of `coord`."""
    coord = (400.0, 300.0)
    radius = 120.0
    pt = overshoot(coord, radius)
    dist = math.sqrt((pt[0] - coord[0])**2 + (pt[1] - coord[1])**2)
    assert dist <= radius, f"Overshoot exceeded radius: dist={dist:.1f} > {radius}"


def test_fitts_steps_minimum():
    """Very short moves should still return at least 25 steps."""
    steps = fitts_steps(distance=10.0, width=100.0)
    assert steps >= 25


def test_fitts_steps_scales_with_distance():
    """Longer distances should produce more steps than shorter distances."""
    short = fitts_steps(distance=50.0)
    long_ = fitts_steps(distance=1000.0)
    assert long_ > short


class MockMouse:
    def __init__(self, raise_error=False):
        self.points = []
        self.raise_error = raise_error

    def move(self, x, y):
        if self.raise_error:
            raise RuntimeError("Mouse connection lost")
        self.points.append((x, y))


class MockPage:
    def __init__(self, raise_error=False):
        self.mouse = MockMouse(raise_error=raise_error)


def test_move_sends_waypoints_to_page():
    """move() should call page.mouse.move() with generated waypoints."""
    from src.core.human_mouse import move
    page = MockPage()
    move(page, dest_x=500.0, dest_y=400.0, current_x=100.0, current_y=100.0)
    assert len(page.mouse.points) >= 25
    # Check exact target reached at the end
    assert abs(page.mouse.points[-1][0] - 500.0) < 1e-3
    assert abs(page.mouse.points[-1][1] - 400.0) < 1e-3


def test_move_handles_overshoot():
    """move() over long distance (>500px) triggers overshoot (two Bezier segments)."""
    from src.core.human_mouse import move
    page = MockPage()
    # Distance from (0,0) to (1000, 1000) is ~1414px (> 500px threshold)
    move(page, dest_x=1000.0, dest_y=1000.0, current_x=0.0, current_y=0.0)
    # With overshoot, total points should be sum of two segments
    assert len(page.mouse.points) >= 50
    assert abs(page.mouse.points[-1][0] - 1000.0) < 1e-3
    assert abs(page.mouse.points[-1][1] - 1000.0) < 1e-3


def test_move_suppresses_exceptions():
    """move() must silently catch any page.mouse.move exception to prevent crashing engine."""
    from src.core.human_mouse import move
    page = MockPage(raise_error=True)
    # This should not raise any exception
    move(page, dest_x=500.0, dest_y=400.0)

