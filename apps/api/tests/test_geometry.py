from app.schemas.domain import DoorWindow, FurnitureItem, Room
from app.services.geometry_service import (
    bbox_polygon,
    detect_collisions,
    detect_door_blocking,
    polygon_area_m2,
)


def _item(item_id: str, x: float, y: float) -> FurnitureItem:
    return FurnitureItem(
        id=item_id,
        category="chair",
        room_id="room_1",
        bbox=bbox_polygon(x, y, 1.0, 1.0),
        rotation_deg=0,
        dimensions_m=[1.0, 1.0],
        clearance_m=0.6,
        material_hint=None,
    )


def test_polygon_area_m2_closes_input():
    assert polygon_area_m2([[0, 0], [2, 0], [2, 2], [0, 2]]) == 4


def test_furniture_collision_detection():
    room = Room(
        id="room_1",
        room_type="living_room",
        polygon=[[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]],
        area_m2=16,
        confidence=1,
    )
    errors = detect_collisions([_item("a", 0.5, 0.5), _item("b", 0.8, 0.8)], [], [room])

    assert errors
    assert "overlaps" in errors[0]


def test_door_blocking_detection():
    door = DoorWindow(
        id="door_1",
        type="door",
        wall_id=None,
        bbox=bbox_polygon(1.0, 0.0, 0.9, 0.2),
        width_m=0.9,
        swing_direction="inward",
    )
    errors = detect_door_blocking([_item("cabinet", 1.1, 0.05)], [door])

    assert errors == ["cabinet blocks door door_1"]
