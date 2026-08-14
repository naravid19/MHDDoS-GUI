"""
human_mouse.py — Python port of ghost-cursor's Bezier-based mouse movement.

Reference: resource/ghost-cursor/src/math.ts + resource/ghost-cursor/src/spoof.ts
Algorithm: Cubic Bezier curve with Fitts' Law step count + overshoot correction.
Zero external dependencies (stdlib math + random only).
"""
from __future__ import annotations
import math
import random
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


# ─── Vector math (port of math.ts) ──────────────────────────────────────────

def _sub(a: tuple, b: tuple) -> tuple:
    return (a[0] - b[0], a[1] - b[1])

def _add(a: tuple, b: tuple) -> tuple:
    return (a[0] + b[0], a[1] + b[1])

def _mult(a: tuple, s: float) -> tuple:
    return (a[0] * s, a[1] * s)

def _div(a: tuple, s: float) -> tuple:
    return (a[0] / s, a[1] / s)

def _magnitude(a: tuple) -> float:
    return math.sqrt(a[0]**2 + a[1]**2)

def _unit(a: tuple) -> tuple:
    mag = _magnitude(a)
    return _div(a, mag) if mag > 0 else (0.0, 0.0)

def _set_magnitude(a: tuple, amount: float) -> tuple:
    return _mult(_unit(a), amount)

def _perpendicular(a: tuple) -> tuple:
    return (a[1], -a[0])

def _random_on_line(a: tuple, b: tuple) -> tuple:
    vec = _sub(b, a)
    t = random.random()
    return _add(a, _mult(vec, t))

def _random_normal_line(a: tuple, b: tuple, spread: float) -> tuple[tuple, tuple]:
    mid = _random_on_line(a, b)
    direction = _sub(b, a)
    normal = _perpendicular(direction)
    normal_scaled = _set_magnitude(normal, spread)
    return mid, normal_scaled

def _generate_bezier_anchors(a: tuple, b: tuple, spread: float) -> tuple[tuple, tuple]:
    """Two off-axis control points (same side only — matches ghost-cursor behaviour)."""
    mid, normal = _random_normal_line(a, b, spread)
    side = 1 if random.random() > 0.5 else -1
    offset = _mult(normal, side)
    test_p = _add(mid, offset)
    if test_p[0] < 0 or test_p[1] < 0:
        side = -side
        offset = _mult(normal, side)
    
    def calc() -> tuple:
        return _random_on_line(mid, _add(mid, offset))
    p1, p2 = calc(), calc()
    return (p1, p2) if p1[0] <= p2[0] else (p2, p1)

def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


# ─── Cubic Bezier LUT ────────────────────────────────────────────────────────

def _cubic_bezier_lut(
    p0: tuple, p1: tuple, p2: tuple, p3: tuple, steps: int
) -> list[tuple]:
    """Return `steps+1` points along cubic Bezier P0-P1-P2-P3."""
    pts = []
    for i in range(steps + 1):
        t  = i / steps
        mt = 1 - t
        x  = mt**3*p0[0] + 3*mt**2*t*p1[0] + 3*mt*t**2*p2[0] + t**3*p3[0]
        y  = mt**3*p0[1] + 3*mt**2*t*p1[1] + 3*mt*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts


# ─── Fitts' Law step counter ─────────────────────────────────────────────────

def fitts_steps(
    distance: float,
    width: float = 100.0,
    move_speed: float | None = None,
) -> int:
    """Calculate how many waypoints the path should contain.

    Args:
        distance:   Euclidean distance from start to end in pixels.
        width:      Approximate target element width (default 100 px).
        move_speed: Optional scalar; 1.0=normal, 0.5=slow, 2.0=fast.

    Returns:
        Integer >= 25 (minimum meaningful step count).
    """
    MIN_STEPS = 25
    b = 2
    id_ = math.log2(distance / max(width, 1) + 1)
    fitts_time = b * id_
    speed_scalar = move_speed if move_speed and move_speed > 0 else 1.0
    speed = 25.0 / speed_scalar
    base_time = speed * MIN_STEPS / 25.0
    steps = math.ceil((math.log2(fitts_time + 1) + base_time) * 3)
    return max(steps, MIN_STEPS)


# ─── Overshoot ───────────────────────────────────────────────────────────────

def overshoot(coord: tuple[float, float], radius: float) -> tuple[float, float]:
    """Return a random point within `radius` pixels of `coord`."""
    angle = random.random() * 2 * math.pi
    r = radius * math.sqrt(random.random())
    return (coord[0] + r * math.cos(angle), coord[1] + r * math.sin(angle))


# ─── Core path generator ─────────────────────────────────────────────────────

def generate_bezier_path(
    start: tuple[float, float],
    end: tuple[float, float],
    spread_override: float | None = None,
) -> list[tuple[float, float]]:
    """Generate a list of (x, y) waypoints along a Bezier curve.

    Args:
        start:           (x, y) starting coordinate.
        end:             (x, y) target coordinate.
        spread_override: Optional manual Bezier spread (deviation width).

    Returns:
        List of (x, y) tuples, at least 25 points.
        First point is near `start`, last point is near `end`.
        All coordinates are >= 0.
    """
    MIN_SPREAD, MAX_SPREAD = 2.0, 200.0
    direction = _sub(end, start)
    distance  = _magnitude(direction)
    spread    = spread_override if spread_override is not None \
                else _clamp(distance, MIN_SPREAD, MAX_SPREAD)

    p1, p2 = _generate_bezier_anchors(start, end, spread)
    steps  = fitts_steps(distance)
    raw    = _cubic_bezier_lut(start, p1, p2, end, steps)
    return [(max(0.0, x), max(0.0, y)) for x, y in raw]


# ─── High-level page adapter ─────────────────────────────────────────────────

_OVERSHOOT_THRESHOLD = 500.0   # px — ghost-cursor default
_OVERSHOOT_RADIUS    = 120.0
_OVERSHOOT_SPREAD    = 10.0


def move(
    page: "Any",
    dest_x: float,
    dest_y: float,
    *,
    current_x: float | None = None,
    current_y: float | None = None,
    move_speed: float | None = None,
    step_delay_ms: float = 0.0,
) -> None:
    """Move the page mouse along a human-like Bezier path.

    Replaces bare `page.mouse.move(random.randint(...))` calls.
    Silently suppresses any exception so the solver never crashes.

    Args:
        page:          Playwright-compatible page (`page.mouse.move(x, y)`).
        dest_x:        Target X in pixels.
        dest_y:        Target Y in pixels.
        current_x:     Current cursor X (random default if None).
        current_y:     Current cursor Y (random default if None).
        move_speed:    Speed scalar (None = random each call).
        step_delay_ms: Extra sleep between waypoints in ms (0 = fastest).
    """
    sx = current_x if current_x is not None else random.uniform(100, 500)
    sy = current_y if current_y is not None else random.uniform(100, 400)

    start    = (float(sx), float(sy))
    end      = (float(dest_x), float(dest_y))
    distance = _magnitude(_sub(end, start))

    if distance > _OVERSHOOT_THRESHOLD:
        shoot = overshoot(end, _OVERSHOOT_RADIUS)
        _send(page, generate_bezier_path(start, shoot, _OVERSHOOT_SPREAD), step_delay_ms)
        _send(page, generate_bezier_path(shoot, end, _OVERSHOOT_SPREAD / 2), step_delay_ms)
    else:
        _send(page, generate_bezier_path(start, end), step_delay_ms)


def _send(page: "Any", waypoints: list[tuple], step_delay_ms: float) -> None:
    import inspect
    for x, y in waypoints:
        try:
            if hasattr(page, "actions") and hasattr(page.actions, "move"):
                res = page.actions.move(x, y)
                if inspect.isawaitable(res):
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        asyncio.run(res)
            elif hasattr(page, "mouse") and hasattr(page.mouse, "move"):
                res = page.mouse.move(x, y)
                if inspect.isawaitable(res):
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        loop.create_task(res)
                    except RuntimeError:
                        asyncio.run(res)
        except Exception:
            return
        if step_delay_ms > 0:
            time.sleep(step_delay_ms / 1000.0)


async def async_move(
    page: "Any",
    dest_x: float,
    dest_y: float,
    *,
    current_x: float | None = None,
    current_y: float | None = None,
    move_speed: float | None = None,
    step_delay_ms: float = 0.0,
) -> None:
    """Move the page mouse asynchronously along a human-like Bezier path without blocking the event loop.

    Args:
        page:          Playwright/Camoufox/Patchright async page.
        dest_x:        Target X in pixels.
        dest_y:        Target Y in pixels.
        current_x:     Current cursor X (random default if None).
        current_y:     Current cursor Y (random default if None).
        move_speed:    Speed scalar (None = random each call).
        step_delay_ms: Extra sleep between waypoints in ms (0 = fastest).
    """
    sx = current_x if current_x is not None else random.uniform(100, 500)
    sy = current_y if current_y is not None else random.uniform(100, 400)

    start    = (float(sx), float(sy))
    end      = (float(dest_x), float(dest_y))
    distance = _magnitude(_sub(end, start))

    if distance > _OVERSHOOT_THRESHOLD:
        shoot = overshoot(end, _OVERSHOOT_RADIUS)
        await _async_send(page, generate_bezier_path(start, shoot, _OVERSHOOT_SPREAD), step_delay_ms)
        await _async_send(page, generate_bezier_path(shoot, end, _OVERSHOOT_SPREAD / 2), step_delay_ms)
    else:
        await _async_send(page, generate_bezier_path(start, end), step_delay_ms)


async def _async_send(page: "Any", waypoints: list[tuple], step_delay_ms: float) -> None:
    import asyncio
    import inspect
    for x, y in waypoints:
        try:
            if hasattr(page, "actions") and hasattr(page.actions, "move"):
                res = page.actions.move(x, y)
                if inspect.isawaitable(res):
                    await res
            elif hasattr(page, "mouse") and hasattr(page.mouse, "move"):
                res = page.mouse.move(x, y)
                if inspect.isawaitable(res):
                    await res
        except Exception:
            return
        if step_delay_ms > 0:
            await asyncio.sleep(step_delay_ms / 1000.0)
