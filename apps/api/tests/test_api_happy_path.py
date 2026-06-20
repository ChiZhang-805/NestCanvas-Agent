from io import BytesIO
from pathlib import Path

from PIL import Image


def _png_bytes() -> BytesIO:
    image = Image.new("RGB", (640, 420), color=(250, 247, 240))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_api_happy_path_project_upload_parse_brief_layout(client):
    project_response = client.post("/api/projects", json={"title": "测试两居室"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    upload_response = client.post(
        f"/api/projects/{project_id}/assets",
        files={"file": ("floorplan.png", _png_bytes(), "image/png")},
    )
    assert upload_response.status_code == 201
    assert upload_response.json()["asset_type"] == "image"

    prepare_response = client.post(f"/api/projects/{project_id}/prepare-input")
    assert prepare_response.status_code == 200
    prepared = prepare_response.json()
    assert prepared["source_asset_id"] == upload_response.json()["id"]
    assert prepared["prepared_asset"]["asset_type"] == "prepared_image"
    assert 0 <= prepared["quality_score"] <= 100

    parse_response = client.post(f"/api/projects/{project_id}/parse-floorplan")
    assert parse_response.status_code == 200
    job_id = parse_response.json()["job_id"]

    job_response = client.get(f"/api/jobs/{job_id}")
    assert job_response.status_code == 200
    job_payload = job_response.json()
    assert job_payload["status"] == "completed"
    assert job_payload["result_id"]

    floorplan_response = client.get(f"/api/floorplans/{job_payload['result_id']}")
    assert floorplan_response.status_code == 200
    assert floorplan_response.json()["rooms"]

    brief_response = client.post(
        f"/api/projects/{project_id}/brief",
        json={"text": "一家三口，需要温暖木色、更多收纳和书柜，预算20万。"},
    )
    assert brief_response.status_code == 200
    assert brief_response.json()["storage_level"] == "high"

    layout_response = client.post(f"/api/projects/{project_id}/layout-options")
    assert layout_response.status_code == 200
    options = layout_response.json()
    assert len(options) >= 2
    assert options[0]["furniture_items"]

    regenerated_response = client.post(f"/api/projects/{project_id}/layout-options")
    assert regenerated_response.status_code == 200
    regenerated_options = regenerated_response.json()
    assert len(regenerated_options) == len(options)

    review_response = client.post(f"/api/projects/{project_id}/design-review")
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["best_option_id"]
    assert len(review["option_reviews"]) == len(regenerated_options)
    assert 0 <= review["readiness_score"] <= 100

    living_plan_response = client.post(f"/api/projects/{project_id}/living-plan")
    assert living_plan_response.status_code == 200
    living_plan = living_plan_response.json()
    assert living_plan["selected_option_id"]
    assert living_plan["shopping_items"]
    assert living_plan["budget_phases"]
    assert living_plan["designer_handoff_questions"]

    workflow_response = client.get(f"/api/projects/{project_id}/workflow")
    assert workflow_response.status_code == 200
    workflow = workflow_response.json()
    assert workflow["project_id"] == project_id
    assert workflow["readiness_score"] >= 70
    assert {"floorplan", "brief", "layout_options", "home_coach"}.issubset(
        {step["key"] for step in workflow["steps"]}
    )
    assert {module["key"] for module in workflow["llm_modules"]} >= {
        "vision_floorplan_triage",
        "reasoning_layout_tradeoff",
    }

    home_coach_response = client.post(f"/api/projects/{project_id}/home-coach")
    assert home_coach_response.status_code == 200
    home_coach = home_coach_response.json()
    assert home_coach["selected_option_id"]
    assert home_coach["room_cards"]
    assert home_coach["family_script"]
    assert "room_scene_reasoner" in {module["key"] for module in home_coach["llm_upgrade_plan"]}

    render_response = client.post(f"/api/layout-options/{regenerated_options[0]['id']}/render")
    assert render_response.status_code == 200
    assert render_response.json()["disclaimer"]

    export_response = client.post(f"/api/projects/{project_id}/export")
    assert export_response.status_code == 201
    assert export_response.json()["asset_type"] == "export"
    export_payload = Path(export_response.json()["local_path"]).read_text(encoding="utf-8")
    assert '"workflow"' in export_payload
    assert '"design_review"' in export_payload
    assert '"living_plan"' in export_payload
    assert '"home_coach"' in export_payload

    project_detail_response = client.get(f"/api/projects/{project_id}")
    assert project_detail_response.status_code == 200
    detail = project_detail_response.json()
    assert detail["floorplans"]
    assert detail["briefs"]
    assert len(detail["layout_options"]) == len(regenerated_options)
    assert detail["renders"]
    assert any(asset["asset_type"] == "export" for asset in detail["assets"])


def test_demo_project_creates_ready_layout(client):
    response = client.post("/api/demo-project")

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "示例两居室"
    assert payload["floorplans"]
    assert payload["briefs"]
    assert len(payload["layout_options"]) >= 2


def test_starter_floorplan_allows_no_asset_project(client):
    project_response = client.post("/api/projects", json={"title": "无图项目"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    starter_response = client.post(f"/api/projects/{project_id}/starter-floorplan")

    assert starter_response.status_code == 200
    payload = starter_response.json()
    assert payload["project_id"] == project_id
    assert payload["rooms"]
    assert payload["confidence"] < 0.5
    assert any("草稿底图" in warning for warning in payload["warnings"])


def test_floorplan_library_search_and_select_template(client):
    library_response = client.get("/api/floorplan-library?query=一家三口%20收纳&bedrooms=2")
    assert library_response.status_code == 200
    library = library_response.json()
    assert library["sources"]
    assert library["items"]
    assert library["items"][0]["floorplan"]["rooms"]

    project_response = client.post("/api/projects", json={"title": "户型库项目"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]
    template_id = library["items"][0]["id"]

    select_response = client.post(f"/api/projects/{project_id}/library-floorplan/{template_id}")

    assert select_response.status_code == 200
    selected = select_response.json()
    assert selected["project_id"] == project_id
    assert selected["rooms"]
    assert any("户型库" in warning for warning in selected["warnings"])


def test_openai_settings_status_accepts_browser_key_header(client):
    mock_response = client.get("/api/settings/openai")
    assert mock_response.status_code == 200
    assert mock_response.json()["source"] == "mock"

    browser_response = client.get(
        "/api/settings/openai", headers={"X-OpenAI-API-Key": "sk-test-browser-key"}
    )
    assert browser_response.status_code == 200
    payload = browser_response.json()
    assert payload["source"] == "browser"
    assert payload["active"] is True


def test_upload_suffix_follows_content_type_not_filename(client):
    project_response = client.post("/api/projects", json={"title": "扩展名错配"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    image_response = client.post(
        f"/api/projects/{project_id}/assets",
        files={"file": ("misnamed.pdf", _png_bytes(), "image/jpeg")},
    )
    assert image_response.status_code == 201
    image_payload = image_response.json()
    assert image_payload["asset_type"] == "image"
    assert image_payload["local_path"].endswith(".jpg")

    pdf_response = client.post(
        f"/api/projects/{project_id}/assets",
        files={"file": ("misnamed.jpg", BytesIO(b"%PDF-1.4\n% nestcanvas test\n"), "application/pdf")},
    )
    assert pdf_response.status_code == 201
    pdf_payload = pdf_response.json()
    assert pdf_payload["asset_type"] == "pdf"
    assert pdf_payload["local_path"].endswith(".pdf")
