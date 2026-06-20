from __future__ import annotations

import math
from itertools import combinations
from typing import Any

from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.geometry.polygon import orient

from app.schemas.domain import DoorWindow, FurnitureItem, Wall


PointLike = list[float] | tuple[float, float]
WALL_ANCHORED_CATEGORIES = {
    "bed",
    "bookshelf",
    "counter",
    "low_drawer",
    "nightstand",
    "sofa",
    "toilet",
    "toy_storage",
    "tv_console",
    "vanity",
    "wardrobe",
}
ADJACENT_ALLOWED_CATEGORY_PAIRS = {
    frozenset(("bed", "nightstand")),
    frozenset(("toilet", "vanity")),
}


def _as_mapping(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _polygon_from_points(points: list[PointLike]) -> Polygon:
    normalized = normalize_polygon(points)
    return Polygon(normalized)


def normalize_polygon(points: list[PointLike]) -> list[list[float]]:
    cleaned: list[list[float]] = []
    for point in points:
        current = [float(point[0]), float(point[1])]
        if not cleaned or cleaned[-1] != current:
            cleaned.append(current)

    if len(cleaned) < 3:
        raise ValueError("A polygon requires at least three unique points.")

    if cleaned[0] != cleaned[-1]:
        cleaned.append(cleaned[0])

    poly = Polygon(cleaned)
    if not poly.is_valid:
        poly = poly.buffer(0)
    if poly.is_empty:
        raise ValueError("Polygon cannot be repaired.")

    poly = orient(poly, sign=1.0)
    return [[round(x, 4), round(y, 4)] for x, y in poly.exterior.coords]


def polygon_area_m2(points: list[PointLike]) -> float:
    return round(abs(_polygon_from_points(points).area), 4)


def bbox_polygon(
    x: float, y: float, w: float, h: float, rotation_deg: float = 0
) -> list[list[float]]:
    poly = Polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)])
    if rotation_deg:
        poly = affinity.rotate(poly, rotation_deg, origin="center", use_radians=False)
    return [[round(px, 4), round(py, 4)] for px, py in poly.exterior.coords]


def furniture_polygon(item: FurnitureItem | dict[str, Any]) -> Polygon:
    data = _as_mapping(item)
    return _polygon_from_points(data["bbox"])


def wall_polygon(wall: Wall | dict[str, Any]) -> Polygon:
    data = _as_mapping(wall)
    line = LineString(data["centerline"])
    return line.buffer(float(data.get("thickness_m", 0.12)) / 2, cap_style="square")


def _room_for_item(item: dict[str, Any], rooms: list[Any]) -> dict[str, Any] | None:
    for room in rooms:
        data = _as_mapping(room)
        if data["id"] == item["room_id"]:
            return data
    return None


def detect_collisions(
    furniture_items: list[FurnitureItem | dict[str, Any]],
    walls: list[Wall | dict[str, Any]],
    rooms: list[Any],
) -> list[str]:
    errors: list[str] = []
    item_data = [_as_mapping(item) for item in furniture_items]

    for left, right in combinations(item_data, 2):
        if left["room_id"] != right["room_id"]:
            continue
        overlap = furniture_polygon(left).intersection(furniture_polygon(right)).area
        if overlap > 0.01:
            errors.append(
                f"{left['id']} overlaps {right['id']} by {round(overlap, 2)} m2"
            )

    wall_polys = [(wall_data["id"], wall_polygon(wall_data)) for wall_data in map(_as_mapping, walls)]
    for item in item_data:
        item_poly = furniture_polygon(item)
        room = _room_for_item(item, rooms)
        if room is not None:
            room_poly = _polygon_from_points(room["polygon"])
            if not room_poly.buffer(0.01).covers(item_poly):
                errors.append(f"{item['id']} is outside room {room['id']}")

        for wall_id, wall_poly in wall_polys:
            if item_poly.intersects(wall_poly) and item_poly.intersection(wall_poly).area > 0.01:
                errors.append(f"{item['id']} intersects wall {wall_id}")

    return errors


def detect_door_blocking(
    furniture_items: list[FurnitureItem | dict[str, Any]],
    doors: list[DoorWindow | dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    door_polys = [(door_data["id"], _polygon_from_points(door_data["bbox"])) for door_data in map(_as_mapping, doors)]
    for item in map(_as_mapping, furniture_items):
        item_poly = furniture_polygon(item)
        for door_id, door_poly in door_polys:
            if item_poly.intersection(door_poly).area > 0.01:
                errors.append(f"{item['id']} blocks door {door_id}")
    return errors


def min_clearance_check(
    furniture_items: list[FurnitureItem | dict[str, Any]],
    room_polygon: list[PointLike],
    threshold_m: float,
) -> list[str]:
    warnings: list[str] = []
    room = _polygon_from_points(room_polygon)
    furniture = [_as_mapping(item) for item in furniture_items]

    for item in furniture:
        poly = furniture_polygon(item)
        if not room.buffer(0.01).covers(poly):
            warnings.append(f"{item['id']} has no valid clearance because it is outside the room")
            continue
        distance_to_wall = poly.distance(room.boundary)
        if (
            item.get("category") not in WALL_ANCHORED_CATEGORIES
            and 0 < distance_to_wall < threshold_m
        ):
            warnings.append(
                f"{item['id']} is {round(distance_to_wall, 2)} m from wall; target is {threshold_m} m"
            )

    for left, right in combinations(furniture, 2):
        if left["room_id"] != right["room_id"]:
            continue
        gap = furniture_polygon(left).distance(furniture_polygon(right))
        required = min(float(left.get("clearance_m", threshold_m)), float(right.get("clearance_m", threshold_m)))
        category_pair = frozenset((str(left.get("category")), str(right.get("category"))))
        if category_pair in ADJACENT_ALLOWED_CATEGORY_PAIRS:
            continue
        if 0 < gap < required:
            warnings.append(
                f"{left['id']} and {right['id']} have {round(gap, 2)} m clearance; target is {required} m"
            )
    return warnings


def score_layout(option: Any) -> float:
    data = _as_mapping(option)
    hard_errors = data.get("hard_errors", [])
    soft_warnings = data.get("soft_warnings", [])
    metrics = data.get("metrics", {})

    base = 100.0
    base -= 28.0 * len(hard_errors)
    base -= 4.0 * len(soft_warnings)
    base += min(float(metrics.get("storage_units", 0)) * 1.5, 6)
    base += min(float(metrics.get("rooms_furnished", 0)) * 1.0, 5)
    return round(max(0.0, min(100.0, base)), 1)


def polygon_bounds(points: list[PointLike]) -> tuple[float, float, float, float]:
    poly = _polygon_from_points(points)
    minx, miny, maxx, maxy = poly.bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def polygon_center(points: list[PointLike]) -> tuple[float, float]:
    minx, miny, maxx, maxy = polygon_bounds(points)
    return (minx + maxx) / 2, (miny + maxy) / 2


def rotate_dimensions(width: float, height: float, rotation_deg: float) -> tuple[float, float]:
    radians = math.radians(rotation_deg % 180)
    rotated_w = abs(width * math.cos(radians)) + abs(height * math.sin(radians))
    rotated_h = abs(width * math.sin(radians)) + abs(height * math.cos(radians))
    return rotated_w, rotated_h
