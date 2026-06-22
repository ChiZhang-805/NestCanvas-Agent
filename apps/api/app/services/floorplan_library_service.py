from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from app.schemas.domain import (
    DoorWindow,
    FloorPlan,
    FloorPlanDatasetSource,
    FloorPlanLibraryItem,
    Room,
)
from app.services.geometry_service import normalize_polygon, polygon_area_m2


QUERY_SYNONYMS: dict[str, tuple[str, ...]] = {
    "一家三口": ("family", "small_family", "school_age_child", "two_bedroom"),
    "三口之家": ("family", "small_family", "school_age_child", "two_bedroom"),
    "亲子": ("family", "school_age_child", "three_bedroom"),
    "孩子": ("family", "school_age_child", "child"),
    "儿童": ("family", "school_age_child", "child"),
    "二孩": ("family", "high_storage", "three_bedroom"),
    "老人": ("elderly", "multi_generation", "guest_room"),
    "老人房": ("elderly", "multi_generation", "guest_room"),
    "三代": ("multi_generation", "elderly", "four_bedroom"),
    "收纳": ("storage", "high_storage"),
    "高收纳": ("storage", "high_storage"),
    "储物": ("storage", "high_storage"),
    "采光": ("daylight", "balcony"),
    "阳台": ("balcony", "daylight"),
    "办公": ("work_from_home", "study"),
    "书房": ("study", "work_from_home"),
    "独居": ("single", "studio", "one_bedroom"),
    "情侣": ("couple", "one_bedroom"),
    "开间": ("studio", "single"),
    "四房": ("four_bedroom", "multi_generation"),
    "四居": ("four_bedroom", "multi_generation"),
    "三房": ("three_bedroom", "family"),
    "三居": ("three_bedroom", "family"),
    "两房": ("two_bedroom", "family"),
    "两居": ("two_bedroom", "family"),
}


def _expand_query_tokens(value: str | None) -> list[str]:
    normalized = (value or "").lower().replace(",", " ").replace("，", " ")
    raw_tokens = [token.strip() for token in normalized.split() if token.strip()]
    expanded: set[str] = set(raw_tokens)
    compact = normalized.replace(" ", "")
    for keyword, synonyms in QUERY_SYNONYMS.items():
        if keyword.lower() in normalized or keyword.lower() in compact:
            expanded.add(keyword.lower())
            expanded.update(token.lower() for token in synonyms)
    return sorted(expanded)


def _rect(x: float, y: float, width: float, height: float) -> list[list[float]]:
    return normalize_polygon(
        [
            [x, y],
            [x + width, y],
            [x + width, y + height],
            [x, y + height],
        ]
    )


def _room(room_id: str, room_type: str, x: float, y: float, width: float, height: float) -> Room:
    polygon = _rect(x, y, width, height)
    return Room(
        id=room_id,
        room_type=room_type,
        polygon=polygon,
        area_m2=polygon_area_m2(polygon),
        confidence=0.92,
    )


def _opening(
    opening_id: str,
    opening_type: Literal["door", "window"],
    x: float,
    y: float,
    width: float,
    height: float,
) -> DoorWindow:
    return DoorWindow(
        id=opening_id,
        type=opening_type,
        wall_id=None,
        bbox=_rect(x, y, width, height),
        width_m=max(width, height),
        swing_direction=None,
    )


def _plan(width: float, height: float, rooms: list[Room], warnings: list[str] | None = None) -> FloorPlan:
    return FloorPlan(
        version="1.0",
        unit="m",
        scale_m_per_px=0.025,
        boundary=_rect(0, 0, width, height),
        rooms=rooms,
        walls=[],
        doors=[
            _opening("door_entry", "door", 0.7, 0.05, 0.9, 0.14),
        ],
        windows=[
            _opening("window_living", "window", max(1.0, width - 3.0), height - 0.18, 1.8, 0.14),
        ],
        warnings=warnings or ["Template floorplan from NestCanvas library; calibrate before final delivery."],
        confidence=0.74,
    )


DATASET_SOURCES = [
    FloorPlanDatasetSource(
        id="rplan",
        name="RPLAN",
        url="https://wutomwu.github.io/particulars.html?id=1",
        license="Research dataset; redistribution/commercial terms need manual verification.",
        commercial_use="unknown",
        recommended_use="Large-scale residential layout retrieval and statistics.",
        notes=[
            "Large synthetic/realistic residential floorplan corpus commonly used in layout generation research.",
            "Good candidate for bedroom-count, area, room-adjacency and outline-shape retrieval.",
        ],
    ),
    FloorPlanDatasetSource(
        id="cubicasa5k",
        name="CubiCasa5K",
        url="https://github.com/CubiCasa/CubiCasa5k",
        license="CC BY-NC 4.0",
        commercial_use="restricted",
        recommended_use="Training and evaluating floorplan parsing, not direct commercial template library use.",
        notes=[
            "5k floorplan images with semantic annotations.",
            "Non-commercial license means it is useful for research prototypes and parser evaluation.",
        ],
    ),
    FloorPlanDatasetSource(
        id="swiss_dwellings",
        name="Swiss Dwellings",
        url="https://zenodo.org/records/7788422",
        license="CC BY 4.0",
        commercial_use="allowed",
        recommended_use="Advanced retrieval with geometry, accessibility, light/noise and dwelling indicators.",
        notes=[
            "Useful as inspiration for richer search facets beyond room count and area.",
            "Requires attribution; check whether downstream product redistribution needs additional review.",
        ],
    ),
    FloorPlanDatasetSource(
        id="nestcanvas_seed",
        name="NestCanvas Seed Templates",
        url="local://nestcanvas/seed-floorplans",
        license="Internal synthetic seed templates",
        commercial_use="allowed",
        recommended_use="Product demo, fallback starts and schema-compatible retrieval tests.",
        notes=[
            "Small hand-authored library used while public datasets are being normalized.",
            "Not copied from external datasets.",
        ],
    ),
]


@dataclass(frozen=True)
class LibraryTemplate:
    id: str
    title: str
    source_dataset_id: str
    area_m2: float
    bedrooms: int
    bathrooms: int
    region: str
    tags: tuple[str, ...]
    household_fit: tuple[str, ...]
    floorplan: FloorPlan


def _templates() -> list[LibraryTemplate]:
    return [
        LibraryTemplate(
            id="seed_studio_38",
            title="38 m2 开放式单身公寓",
            source_dataset_id="nestcanvas_seed",
            area_m2=38,
            bedrooms=0,
            bathrooms=1,
            region="compact_city",
            tags=("studio", "single", "low_budget", "open_living", "rental"),
            household_fit=("独居", "短租", "年轻白领"),
            floorplan=_plan(
                6.4,
                5.9,
                [
                    _room("room_living_sleeping", "living_room", 0.2, 0.2, 4.1, 3.8),
                    _room("room_kitchen", "kitchen", 4.5, 0.2, 1.7, 2.2),
                    _room("room_bathroom", "bathroom", 4.5, 2.6, 1.7, 1.7),
                    _room("room_balcony", "balcony", 0.2, 4.2, 3.8, 1.5),
                ],
            ),
        ),
        LibraryTemplate(
            id="seed_1br_55",
            title="55 m2 一居紧凑收纳型",
            source_dataset_id="nestcanvas_seed",
            area_m2=55,
            bedrooms=1,
            bathrooms=1,
            region="compact_city",
            tags=("one_bedroom", "storage", "couple", "compact", "work_from_home"),
            household_fit=("独居", "情侣", "居家办公"),
            floorplan=_plan(
                7.8,
                6.9,
                [
                    _room("room_living", "living_room", 0.2, 0.2, 3.7, 3.4),
                    _room("room_dining_kitchen", "dining_room", 4.1, 0.2, 3.5, 2.7),
                    _room("room_master", "master_bedroom", 0.2, 3.8, 3.9, 2.9),
                    _room("room_bathroom", "bathroom", 4.3, 3.2, 1.8, 1.8),
                    _room("room_storage", "storage", 6.3, 3.2, 1.3, 1.8),
                ],
            ),
        ),
        LibraryTemplate(
            id="seed_2br_72",
            title="72 m2 两居通用改善型",
            source_dataset_id="nestcanvas_seed",
            area_m2=72,
            bedrooms=2,
            bathrooms=1,
            region="mainstream_cn",
            tags=("two_bedroom", "family", "balanced", "storage", "school_age_child"),
            household_fit=("一家三口", "新婚过渡", "长住"),
            floorplan=_plan(
                9.8,
                7.2,
                [
                    _room("room_living", "living_room", 0.2, 0.2, 4.6, 3.7),
                    _room("room_kitchen_dining", "dining_room", 5.0, 0.2, 4.6, 2.8),
                    _room("room_master", "master_bedroom", 0.2, 4.1, 4.7, 2.9),
                    _room("room_child", "bedroom", 5.1, 4.1, 2.5, 2.9),
                    _room("room_bathroom", "bathroom", 7.8, 4.1, 1.8, 1.7),
                ],
            ),
        ),
        LibraryTemplate(
            id="seed_2br_long_68",
            title="68 m2 长条两居采光优先",
            source_dataset_id="nestcanvas_seed",
            area_m2=68,
            bedrooms=2,
            bathrooms=1,
            region="mainstream_cn",
            tags=("two_bedroom", "long_narrow", "daylight", "balcony", "small_family"),
            household_fit=("一家三口", "老人同住短期", "重视采光"),
            floorplan=_plan(
                11.2,
                6.0,
                [
                    _room("room_living_dining", "living_room", 0.2, 0.2, 5.0, 3.0),
                    _room("room_kitchen", "kitchen", 5.4, 0.2, 2.2, 2.2),
                    _room("room_master", "master_bedroom", 0.2, 3.4, 4.0, 2.4),
                    _room("room_child", "bedroom", 4.5, 3.4, 3.0, 2.4),
                    _room("room_bathroom", "bathroom", 7.9, 0.2, 1.8, 1.8),
                    _room("room_balcony", "balcony", 7.9, 3.4, 3.1, 2.4),
                ],
            ),
        ),
        LibraryTemplate(
            id="seed_3br_105",
            title="105 m2 三居亲子收纳型",
            source_dataset_id="nestcanvas_seed",
            area_m2=105,
            bedrooms=3,
            bathrooms=2,
            region="improvement_cn",
            tags=("three_bedroom", "family", "high_storage", "two_bathrooms", "study"),
            household_fit=("二孩家庭", "三代短住", "长期改善"),
            floorplan=_plan(
                11.5,
                9.0,
                [
                    _room("room_living", "living_room", 0.2, 0.2, 5.2, 4.1),
                    _room("room_kitchen_dining", "dining_room", 5.7, 0.2, 5.6, 3.2),
                    _room("room_master", "master_bedroom", 0.2, 4.6, 4.2, 4.2),
                    _room("room_child_1", "bedroom", 4.7, 4.6, 3.0, 4.2),
                    _room("room_child_2", "bedroom", 8.0, 4.6, 3.3, 2.8),
                    _room("room_bath_1", "bathroom", 8.0, 7.6, 1.6, 1.2),
                    _room("room_bath_2", "bathroom", 9.8, 7.6, 1.5, 1.2),
                ],
            ),
        ),
        LibraryTemplate(
            id="seed_4br_128",
            title="128 m2 四房多代同住型",
            source_dataset_id="nestcanvas_seed",
            area_m2=128,
            bedrooms=4,
            bathrooms=2,
            region="large_family_cn",
            tags=("four_bedroom", "multi_generation", "elderly", "guest_room", "storage"),
            household_fit=("三代同住", "老人房", "家庭会客"),
            floorplan=_plan(
                13.0,
                9.8,
                [
                    _room("room_living", "living_room", 0.2, 0.2, 5.6, 4.0),
                    _room("room_dining_kitchen", "dining_room", 6.1, 0.2, 6.7, 3.1),
                    _room("room_master", "master_bedroom", 0.2, 4.5, 4.3, 5.1),
                    _room("room_elder", "bedroom", 4.8, 4.5, 3.0, 2.8),
                    _room("room_child", "bedroom", 8.1, 4.5, 2.8, 2.8),
                    _room("room_guest", "bedroom", 10.2, 4.5, 2.6, 2.8),
                    _room("room_bath_1", "bathroom", 4.8, 7.6, 1.8, 2.0),
                    _room("room_bath_2", "bathroom", 6.9, 7.6, 1.8, 2.0),
                    _room("room_storage", "storage", 9.0, 7.6, 1.0, 2.0),
                ],
            ),
        ),
    ]


def list_dataset_sources() -> list[FloorPlanDatasetSource]:
    return DATASET_SOURCES


def _source_for(source_id: str) -> FloorPlanDatasetSource:
    return next(source for source in DATASET_SOURCES if source.id == source_id)


def _score_template(
    template: LibraryTemplate,
    query_tokens: Iterable[str],
    bedrooms: int | None,
    min_area: float | None,
    max_area: float | None,
    dataset: str | None,
    tag_tokens: set[str],
) -> float:
    score = 42.0
    searchable = " ".join(
        [
            template.title,
            template.region,
            " ".join(template.tags),
            " ".join(template.household_fit),
        ]
    ).lower()

    for token in query_tokens:
        if token and token.lower() in searchable:
            score += 12

    if bedrooms is not None:
        distance = abs(template.bedrooms - bedrooms)
        score += max(0, 24 - distance * 10)

    if min_area is not None and template.area_m2 >= min_area:
        score += 6
    if max_area is not None and template.area_m2 <= max_area:
        score += 6
    if dataset and template.source_dataset_id == dataset:
        score += 10
    if tag_tokens:
        score += len(tag_tokens.intersection(set(template.tags))) * 9

    return round(min(score, 100.0), 1)


def search_floorplan_library(
    query: str | None = None,
    bedrooms: int | None = None,
    min_area: float | None = None,
    max_area: float | None = None,
    dataset: str | None = None,
    tags: str | None = None,
    limit: int = 12,
) -> list[FloorPlanLibraryItem]:
    query_tokens = _expand_query_tokens(query)
    tag_tokens = set(_expand_query_tokens(tags))
    results: list[FloorPlanLibraryItem] = []

    for template in _templates():
        if dataset and template.source_dataset_id != dataset:
            continue
        if bedrooms is not None and abs(template.bedrooms - bedrooms) > 1:
            continue
        if min_area is not None and template.area_m2 < min_area:
            continue
        if max_area is not None and template.area_m2 > max_area:
            continue
        if tag_tokens and not tag_tokens.intersection(set(template.tags)):
            continue

        source = _source_for(template.source_dataset_id)
        results.append(
            FloorPlanLibraryItem(
                id=template.id,
                title=template.title,
                source_dataset_id=source.id,
                source_dataset_name=source.name,
                source_url=source.url,
                license=source.license,
                commercial_use=source.commercial_use,
                area_m2=template.area_m2,
                bedrooms=template.bedrooms,
                bathrooms=template.bathrooms,
                region=template.region,
                tags=list(template.tags),
                household_fit=list(template.household_fit),
                match_score=_score_template(
                    template, query_tokens, bedrooms, min_area, max_area, dataset, tag_tokens
                ),
                floorplan=template.floorplan,
            )
        )

    return sorted(results, key=lambda item: item.match_score, reverse=True)[: max(1, min(limit, 50))]


def get_floorplan_template(template_id: str) -> FloorPlanLibraryItem | None:
    matches = [item for item in search_floorplan_library(limit=50) if item.id == template_id]
    return matches[0] if matches else None
