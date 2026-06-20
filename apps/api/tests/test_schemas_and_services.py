import json
from datetime import datetime, timezone

from app.core.config import Settings
from app.schemas.domain import (
    DesignBrief,
    DesignBriefDocument,
    FloorPlan,
    FloorPlanDocument,
    LayoutOption,
    LayoutOptionDocument,
    ProjectDetail,
)
from app.services.home_coach_service import build_home_coach_package
from app.services.living_plan_service import build_living_plan_package
from app.services.openai_service import parse_design_brief
from app.services.project_workflow_service import build_project_workflow


def test_floorplan_schema_valid(fixture_dir):
    payload = json.loads((fixture_dir / "simple_2br_floorplan.json").read_text())
    floorplan = FloorPlan.model_validate(payload)

    assert floorplan.unit == "m"
    assert floorplan.rooms[0].area_m2 > 10
    assert floorplan.boundary[0] == floorplan.boundary[-1]


def test_design_brief_mock_parse_is_deterministic():
    text = "一家三口，喜欢温暖木色，需要更多收纳和一整面书柜，预算20万，避免暗色。"

    first = parse_design_brief(text)
    second = parse_design_brief(text)

    assert first == second
    assert first.storage_level == "high"
    assert "large_bookshelf" in first.must_have
    assert "child" in first.residents


def test_settings_accept_comma_separated_cors_origins():
    settings = Settings(CORS_ORIGINS="http://localhost:3010, http://127.0.0.1:3011")

    assert settings.cors_origins == ["http://localhost:3010", "http://127.0.0.1:3011"]


def test_fixture_design_brief_and_layout_option_valid(fixture_dir):
    brief = DesignBrief.model_validate_json(
        (fixture_dir / "sample_design_brief.json").read_text()
    )
    option = LayoutOption.model_validate_json(
        (fixture_dir / "sample_layout_option.json").read_text()
    )

    assert brief.style == "warm_wood_minimal"
    assert option.score >= 90


def test_living_plan_package_translates_layout_to_consumer_checklist(fixture_dir):
    floorplan = FloorPlan.model_validate_json(
        (fixture_dir / "simple_2br_floorplan.json").read_text()
    )
    brief = DesignBrief.model_validate_json(
        (fixture_dir / "sample_design_brief.json").read_text()
    )
    option = LayoutOption.model_validate_json(
        (fixture_dir / "sample_layout_option.json").read_text()
    )

    package = build_living_plan_package("proj_test", floorplan, [option], brief)

    assert package.selected_option_id == option.id
    assert package.shopping_items
    assert package.budget_total_high_cny >= package.budget_total_low_cny
    assert package.family_discussion_cards
    assert package.designer_handoff_questions


def test_home_coach_package_extends_consumer_workflow(fixture_dir):
    floorplan = FloorPlan.model_validate_json(
        (fixture_dir / "simple_2br_floorplan.json").read_text()
    )
    brief = DesignBrief.model_validate_json(
        (fixture_dir / "sample_design_brief.json").read_text()
    )
    option = LayoutOption.model_validate_json(
        (fixture_dir / "sample_layout_option.json").read_text()
    )
    floorplan_doc = FloorPlanDocument.model_validate(
        {**floorplan.model_dump(mode="json"), "id": "fp_test", "project_id": "proj_test"}
    )
    brief_doc = DesignBriefDocument.model_validate(
        {**brief.model_dump(mode="json"), "id": "brief_test", "project_id": "proj_test"}
    )
    option_doc = LayoutOptionDocument.model_validate(
        {
            **option.model_dump(mode="json"),
            "project_id": "proj_test",
            "floorplan_id": "fp_test",
            "brief_id": "brief_test",
        }
    )
    detail = ProjectDetail(
        id="proj_test",
        title="家庭教练测试",
        created_at=datetime.now(timezone.utc),
        status="active",
        floorplans=[floorplan_doc],
        briefs=[brief_doc],
        layout_options=[option_doc],
    )

    workflow = build_project_workflow(detail)
    living_plan = build_living_plan_package("proj_test", floorplan, [option], brief)
    coach = build_home_coach_package(
        project_id="proj_test",
        workflow=workflow,
        floorplan=floorplan,
        brief=brief,
        layout_options=[option],
        living_plan=living_plan,
    )

    assert workflow.readiness_score >= 70
    assert coach.selected_option_id == option.id
    assert len(coach.room_cards) == len(floorplan.rooms)
    assert coach.family_script
    assert "designer_handoff_json" in {service.key for service in coach.portable_services}
    assert "room_scene_reasoner" in {service.key for service in coach.llm_upgrade_plan}
