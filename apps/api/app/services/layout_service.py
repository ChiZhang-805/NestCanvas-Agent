from __future__ import annotations

from collections import defaultdict
from typing import Literal
from uuid import uuid4

from app.schemas.domain import DesignBrief, FloorPlan, FurnitureItem, LayoutOption, Room
from app.services.geometry_service import (
    bbox_polygon,
    detect_collisions,
    detect_door_blocking,
    min_clearance_check,
    polygon_bounds,
    score_layout,
)


LayoutStrategy = Literal["balanced_storage", "open_living", "family_friendly"]

STRATEGIES: tuple[LayoutStrategy, ...] = ("balanced_storage", "open_living", "family_friendly")


def _new_item_id(strategy: str, category: str) -> str:
    return f"fur_{strategy[:3]}_{category}_{uuid4().hex[:6]}"


def _item(
    strategy: str,
    category: str,
    room_id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    rotation_deg: float = 0,
    clearance_m: float = 0.6,
    material_hint: str | None = None,
) -> FurnitureItem:
    return FurnitureItem(
        id=_new_item_id(strategy, category),
        category=category,
        room_id=room_id,
        bbox=bbox_polygon(x, y, w, h, rotation_deg),
        rotation_deg=rotation_deg,
        dimensions_m=[round(w, 2), round(h, 2)],
        clearance_m=clearance_m,
        material_hint=material_hint,
    )


def _room_size(room: Room) -> tuple[float, float, float, float, float, float]:
    minx, miny, maxx, maxy = polygon_bounds(room.polygon)
    return minx, miny, maxx, maxy, maxx - minx, maxy - miny


def _living_room_items(room: Room, strategy: str, brief: DesignBrief) -> list[FurnitureItem]:
    minx, miny, maxx, maxy, width, height = _room_size(room)
    items = [
        _item(
            strategy,
            "sofa",
            room.id,
            minx + 0.35,
            maxy - 1.2,
            min(2.3, max(1.8, width - 1.2)),
            0.85,
            material_hint="linen fabric",
        ),
        _item(
            strategy,
            "coffee_table",
            room.id,
            minx + width * 0.42,
            miny + height * 0.39,
            1.0,
            0.55,
            clearance_m=0.45,
            material_hint="oak",
        ),
        _item(
            strategy,
            "tv_console",
            room.id,
            maxx - 1.8,
            miny + 0.35,
            1.45,
            0.38,
            clearance_m=0.45,
            material_hint="warm white lacquer",
        ),
    ]
    if strategy != "open_living" or brief.storage_level == "high":
        items.append(
            _item(
                strategy,
                "bookshelf",
                room.id,
                maxx - 0.65,
                maxy - 1.75,
                0.38,
                1.35,
                clearance_m=0.35,
                material_hint="oak veneer",
            )
        )
    if strategy == "family_friendly":
        items.append(
            _item(
                strategy,
                "toy_storage",
                room.id,
                minx + 0.35,
                miny + 0.35,
                0.9,
                0.42,
                clearance_m=0.5,
                material_hint="rounded corner plywood",
            )
        )
    return items


def _bedroom_items(room: Room, strategy: str, primary: bool) -> list[FurnitureItem]:
    minx, miny, maxx, maxy, width, height = _room_size(room)
    bed_w = 1.8 if primary and width >= 3.4 else 1.5
    bed_h = 2.0
    bed_x = minx + max(0.35, (width - bed_w) / 2)
    bed_y = miny + 0.25
    items = [
        _item(
            strategy,
            "bed",
            room.id,
            bed_x,
            bed_y,
            bed_w,
            bed_h,
            clearance_m=0.55 if strategy == "family_friendly" else 0.5,
            material_hint="upholstered headboard",
        ),
        _item(
            strategy,
            "wardrobe",
            room.id,
            maxx - 1.9,
            maxy - 0.65,
            1.55,
            0.48,
            clearance_m=0.45,
            material_hint="matte white",
        ),
    ]
    if width >= 2.8:
        items.append(
            _item(
                strategy,
                "nightstand",
                room.id,
                max(minx + 0.3, bed_x - 0.55),
                bed_y + 0.15,
                0.42,
                0.42,
                clearance_m=0.35,
                material_hint="oak",
            )
        )
    if strategy == "balanced_storage" and primary and width >= 3.2 and height >= 2.6:
        items.append(
            _item(
                strategy,
                "low_drawer",
                room.id,
                minx + 0.3,
                maxy - 1.2,
                0.48,
                0.9,
                clearance_m=0.35,
                material_hint="oak",
            )
        )
    return items


def _dining_or_kitchen_items(room: Room, strategy: str) -> list[FurnitureItem]:
    minx, miny, maxx, maxy, width, height = _room_size(room)
    if "kitchen" in room.room_type:
        counter_width = max(0.6, min(2.4, width - 0.7))
        return [
            _item(
                strategy,
                "counter",
                room.id,
                minx + 0.35,
                miny + 0.35,
                counter_width,
                0.6,
                clearance_m=0.7,
                material_hint="quartz countertop",
            )
        ]
    table_w = 1.45 if strategy != "open_living" else 1.2
    table_h = 0.85
    return [
        _item(
            strategy,
            "dining_table",
            room.id,
            minx + (width - table_w) / 2,
            miny + (height - table_h) / 2,
            table_w,
            table_h,
            clearance_m=0.75,
            material_hint="oak",
        )
    ]


def _bathroom_items(room: Room, strategy: str) -> list[FurnitureItem]:
    minx, miny, _maxx, maxy, _width, _height = _room_size(room)
    return [
        _item(strategy, "vanity", room.id, minx + 0.25, miny + 0.25, 0.65, 0.45, clearance_m=0.4),
        _item(strategy, "toilet", room.id, minx + 1.05, maxy - 0.9, 0.45, 0.65, clearance_m=0.4),
    ]


def _items_for_room(
    room: Room, strategy: str, brief: DesignBrief, bedroom_index: int
) -> list[FurnitureItem]:
    room_type = room.room_type.lower()
    if "living" in room_type:
        return _living_room_items(room, strategy, brief)
    if "bedroom" in room_type:
        return _bedroom_items(room, strategy, primary=bedroom_index == 0)
    if "dining" in room_type or "kitchen" in room_type:
        return _dining_or_kitchen_items(room, strategy)
    if "bathroom" in room_type:
        return _bathroom_items(room, strategy)
    return []


def generate_layout_options(floorplan: FloorPlan, brief: DesignBrief) -> list[LayoutOption]:
    options: list[LayoutOption] = []

    for strategy in STRATEGIES:
        bedroom_index = 0
        items: list[FurnitureItem] = []
        rooms_by_id = {room.id: room for room in floorplan.rooms}
        for room in floorplan.rooms:
            room_items = _items_for_room(room, strategy, brief, bedroom_index)
            if "bedroom" in room.room_type.lower():
                bedroom_index += 1
            items.extend(room_items)

        hard_errors = detect_collisions(items, floorplan.walls, floorplan.rooms)
        hard_errors.extend(detect_door_blocking(items, floorplan.doors))

        room_items_by_id: dict[str, list[FurnitureItem]] = defaultdict(list)
        for item in items:
            room_items_by_id[item.room_id].append(item)

        soft_warnings: list[str] = []
        threshold = 0.75 if strategy == "family_friendly" else 0.6
        for room_id, room_items in room_items_by_id.items():
            room = rooms_by_id[room_id]
            soft_warnings.extend(min_clearance_check(room_items, room.polygon, threshold))

        storage_units = len(
            [item for item in items if item.category in {"wardrobe", "bookshelf", "toy_storage", "low_drawer"}]
        )
        metrics = {
            "generated_items": len(items),
            "rooms_furnished": len(room_items_by_id),
            "storage_units": storage_units,
            "total_furniture_area_m2": round(
                sum(item.dimensions_m[0] * item.dimensions_m[1] for item in items), 2
            ),
        }
        option = LayoutOption(
            id=f"option_{strategy}_{uuid4().hex[:8]}",
            strategy=strategy,
            furniture_items=items,
            score=50,
            hard_errors=hard_errors,
            soft_warnings=soft_warnings,
            metrics=metrics,
        )
        option.score = score_layout(option)
        options.append(option)

    return sorted(options, key=lambda current: current.score, reverse=True)
