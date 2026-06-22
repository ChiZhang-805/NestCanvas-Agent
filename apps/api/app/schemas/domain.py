from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


Point = Annotated[list[float], Field(min_length=2, max_length=2)]
PolygonPoints = Annotated[list[Point], Field(min_length=4)]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    title: str = Field(default="未命名栖画项目", min_length=1, max_length=200)


class Project(APIModel):
    id: str
    title: str
    created_at: datetime
    status: str


AssetType = Literal["image", "pdf", "prepared_image", "render", "export"]


class Asset(APIModel):
    id: str
    project_id: str
    asset_type: AssetType
    local_path: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class Room(BaseModel):
    id: str
    room_type: str
    polygon: PolygonPoints
    area_m2: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class Wall(BaseModel):
    id: str
    centerline: Annotated[list[Point], Field(min_length=2)]
    thickness_m: float = Field(default=0.12, gt=0)
    confidence: float = Field(ge=0, le=1)
    load_bearing_status: Literal[
        "unknown", "user_marked_load_bearing", "user_marked_non_load_bearing"
    ] = "unknown"


class DoorWindow(BaseModel):
    id: str
    type: Literal["door", "window"]
    wall_id: str | None = None
    bbox: PolygonPoints
    width_m: float = Field(gt=0)
    swing_direction: str | None = None


class FloorPlan(BaseModel):
    version: str = "1.0"
    unit: Literal["m"] = "m"
    scale_m_per_px: float = Field(gt=0)
    boundary: PolygonPoints
    rooms: list[Room] = Field(default_factory=list)
    walls: list[Wall] = Field(default_factory=list)
    doors: list[DoorWindow] = Field(default_factory=list)
    windows: list[DoorWindow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)

    @field_validator("boundary")
    @classmethod
    def boundary_is_closed(cls, value: list[Point]) -> list[Point]:
        if value[0] != value[-1]:
            value = [*value, value[0]]
        return value

    @model_validator(mode="after")
    def close_room_and_opening_polygons(self) -> "FloorPlan":
        for room in self.rooms:
            if room.polygon[0] != room.polygon[-1]:
                room.polygon.append(room.polygon[0])
        for opening in [*self.doors, *self.windows]:
            if opening.bbox[0] != opening.bbox[-1]:
                opening.bbox.append(opening.bbox[0])
        return self


class FloorPlanDocument(FloorPlan):
    id: str
    project_id: str
    created_at: datetime | None = None


class FloorPlanDatasetSource(BaseModel):
    id: str
    name: str
    url: str
    license: str
    commercial_use: Literal["allowed", "restricted", "unknown"]
    recommended_use: str
    notes: list[str] = Field(default_factory=list)


class FloorPlanLibraryItem(BaseModel):
    id: str
    title: str
    source_dataset_id: str
    source_dataset_name: str
    source_url: str
    license: str
    commercial_use: Literal["allowed", "restricted", "unknown"]
    area_m2: float = Field(gt=0)
    bedrooms: int = Field(ge=0)
    bathrooms: int = Field(ge=0)
    region: str
    tags: list[str] = Field(default_factory=list)
    household_fit: list[str] = Field(default_factory=list)
    match_score: float = Field(ge=0, le=100)
    preview_image_url: str | None = None
    preview_kind: Literal["floorplan_svg", "image"] = "floorplan_svg"
    floorplan: FloorPlan


class FloorPlanLibrarySearchResponse(BaseModel):
    sources: list[FloorPlanDatasetSource] = Field(default_factory=list)
    items: list[FloorPlanLibraryItem] = Field(default_factory=list)


class DesignBrief(BaseModel):
    style: str = "warm_wood_minimal"
    budget_cny: int | None = Field(default=None, ge=0)
    residents: list[str] = Field(default_factory=list)
    room_priorities: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    storage_level: Literal["low", "medium", "high"] = "medium"
    color_palette: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class DesignBriefDocument(DesignBrief):
    id: str
    project_id: str
    source_text: str | None = None
    created_at: datetime | None = None


class FurnitureItem(BaseModel):
    id: str
    category: str
    room_id: str
    bbox: PolygonPoints
    rotation_deg: float = 0
    dimensions_m: Point
    clearance_m: float = Field(default=0.6, ge=0)
    material_hint: str | None = None

    @field_validator("bbox")
    @classmethod
    def bbox_is_closed(cls, value: list[Point]) -> list[Point]:
        if value[0] != value[-1]:
            value = [*value, value[0]]
        return value


class LayoutOption(BaseModel):
    id: str
    strategy: Literal["balanced_storage", "open_living", "family_friendly"]
    furniture_items: list[FurnitureItem]
    score: float = Field(ge=0, le=100)
    hard_errors: list[str] = Field(default_factory=list)
    soft_warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class LayoutOptionDocument(LayoutOption):
    project_id: str
    floorplan_id: str
    brief_id: str
    created_at: datetime | None = None


class LayoutOptionReview(BaseModel):
    option_id: str
    strategy: str
    headline: str
    scores: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class DesignReview(BaseModel):
    project_id: str
    generated_with: Literal["local_rules", "openai", "mock"] = "local_rules"
    summary: str
    best_option_id: str | None = None
    readiness_score: float = Field(ge=0, le=100)
    global_risks: list[str] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    option_reviews: list[LayoutOptionReview] = Field(default_factory=list)


class WorkflowStep(BaseModel):
    key: str
    label: str
    status: Literal["done", "current", "available", "blocked"]
    artifact_count: int = Field(ge=0)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    automation_hint: str


class PortableServiceSpec(BaseModel):
    key: str
    label: str
    service_type: Literal["api", "worker", "cli", "export"]
    purpose: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    status: Literal["ready", "planned", "blocked"] = "planned"


class ProjectWorkflow(BaseModel):
    project_id: str
    current_step: str
    readiness_score: int = Field(ge=0, le=100)
    summary: str
    steps: list[WorkflowStep] = Field(default_factory=list)
    automation_plan: list[str] = Field(default_factory=list)
    llm_modules: list[PortableServiceSpec] = Field(default_factory=list)
    portable_services: list[PortableServiceSpec] = Field(default_factory=list)


class LivingBudgetPhase(BaseModel):
    key: Literal["move_in_essentials", "comfort_upgrade", "style_finish", "optional_later"]
    label: str
    estimated_budget_cny_min: int = Field(ge=0)
    estimated_budget_cny_max: int = Field(ge=0)
    included_categories: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LivingShoppingItem(BaseModel):
    category: str
    label: str
    room_id: str
    room_type: str
    priority: Literal["must_buy", "reuse_or_buy", "optional"]
    dimensions_m: Point
    estimated_price_cny_low: int = Field(ge=0)
    estimated_price_cny_high: int = Field(ge=0)
    search_keywords: list[str] = Field(default_factory=list)
    material_hint: str | None = None
    why: str


class LivingDiscussionCard(BaseModel):
    topic: str
    prompt: str
    related_rooms: list[str] = Field(default_factory=list)
    decision_hint: str


class LivingPlanPackage(BaseModel):
    project_id: str
    selected_option_id: str
    selected_strategy: str
    generated_with: Literal["local_rules"] = "local_rules"
    household_summary: str
    recommended_next_step: str
    budget_total_low_cny: int = Field(ge=0)
    budget_total_high_cny: int = Field(ge=0)
    budget_fit: Literal["within_budget", "tight", "over_budget", "unknown"]
    budget_phases: list[LivingBudgetPhase] = Field(default_factory=list)
    shopping_items: list[LivingShoppingItem] = Field(default_factory=list)
    reuse_candidates: list[str] = Field(default_factory=list)
    family_discussion_cards: list[LivingDiscussionCard] = Field(default_factory=list)
    designer_handoff_questions: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class HomeCoachRoomCard(BaseModel):
    room_id: str
    room_type: str
    headline: str
    current_furniture: list[str] = Field(default_factory=list)
    daily_use_notes: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    shopping_focus: list[str] = Field(default_factory=list)
    measurement_tasks: list[str] = Field(default_factory=list)
    visual_prompt: str


class HomeCoachPackage(BaseModel):
    project_id: str
    generated_with: Literal["local_rules"] = "local_rules"
    summary: str
    workflow: ProjectWorkflow
    selected_option_id: str | None = None
    room_cards: list[HomeCoachRoomCard] = Field(default_factory=list)
    family_script: list[str] = Field(default_factory=list)
    designer_packet: list[str] = Field(default_factory=list)
    llm_upgrade_plan: list[PortableServiceSpec] = Field(default_factory=list)
    portable_services: list[PortableServiceSpec] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class RenderAsset(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"] = "completed"
    prompt: str
    input_option_id: str
    output_path: str
    disclaimer: str


class RenderAssetDocument(RenderAsset):
    project_id: str
    created_at: datetime | None = None


class BriefRequest(BaseModel):
    text: str = Field(min_length=1)


class ParseJobResponse(BaseModel):
    job_id: str


class InputPreparationResult(BaseModel):
    project_id: str
    source_asset_id: str
    prepared_asset: Asset
    quality_score: float = Field(ge=0, le=100)
    preparation_stage: Literal["prepared", "passthrough"]
    detected_content: Literal["floorplan_like", "document_like", "unknown"] = "unknown"
    operations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    vision_notes: list[str] = Field(default_factory=list)
    crop_bbox_px: list[int] | None = None
    perspective_corrected: bool = False


class JobStatus(APIModel):
    id: str
    status: str
    stage: str
    progress: int
    result_id: str | None = None
    error: str | None = None


class OpenAISettingsStatus(BaseModel):
    active: bool
    source: Literal["browser", "env", "mock"]
    env_key_configured: bool
    request_key_configured: bool
    text_model: str
    fast_model: str
    image_model: str


class ProjectDetail(Project):
    assets: list[Asset] = Field(default_factory=list)
    floorplans: list[FloorPlanDocument] = Field(default_factory=list)
    briefs: list[DesignBriefDocument] = Field(default_factory=list)
    layout_options: list[LayoutOptionDocument] = Field(default_factory=list)
    renders: list[RenderAssetDocument] = Field(default_factory=list)
