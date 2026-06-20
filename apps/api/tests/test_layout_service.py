import json

from app.schemas.domain import DesignBrief, FloorPlan
from app.services.layout_service import generate_layout_options


def test_layout_generation_returns_at_least_two_options(fixture_dir):
    floorplan = FloorPlan.model_validate_json(
        (fixture_dir / "simple_2br_floorplan.json").read_text()
    )
    brief = DesignBrief.model_validate_json(
        (fixture_dir / "sample_design_brief.json").read_text()
    )

    options = generate_layout_options(floorplan, brief)

    assert len(options) >= 2
    assert {option.strategy for option in options} >= {"balanced_storage", "open_living"}
    assert all(option.furniture_items for option in options)
    assert all(0 <= option.score <= 100 for option in options)


def test_layout_generation_keeps_tiny_kitchen_dimensions_positive():
    floorplan = FloorPlan(
        scale_m_per_px=0.025,
        boundary=[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]],
        rooms=[
            {
                "id": "room_kitchen",
                "room_type": "kitchen",
                "polygon": [[0, 0], [0.5, 0], [0.5, 1.2], [0, 1.2], [0, 0]],
                "area_m2": 0.6,
                "confidence": 0.8,
            }
        ],
        walls=[],
        doors=[],
        windows=[],
        warnings=[],
        confidence=0.8,
    )
    brief = DesignBrief()

    options = generate_layout_options(floorplan, brief)

    assert options
    for option in options:
        counters = [item for item in option.furniture_items if item.category == "counter"]
        assert counters
        assert all(item.dimensions_m[0] > 0 and item.dimensions_m[1] > 0 for item in counters)
