from __future__ import annotations

import shutil
import json
from pathlib import Path
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT_DIR, get_settings
from app.db.session import get_db
from app.models.entities import (
    AssetModel,
    DesignBriefModel,
    FloorPlanModel,
    JobModel,
    LayoutOptionModel,
    ProjectModel,
    RenderAssetModel,
)
from app.schemas.domain import (
    Asset,
    BriefRequest,
    DesignBrief,
    DesignBriefDocument,
    DesignReview,
    FloorPlan,
    FloorPlanLibrarySearchResponse,
    FloorPlanDocument,
    HomeCoachPackage,
    InputPreparationResult,
    JobStatus,
    LivingPlanPackage,
    LayoutOptionDocument,
    OpenAISettingsStatus,
    ParseJobResponse,
    Project,
    ProjectCreate,
    ProjectDetail,
    ProjectWorkflow,
    RenderAssetDocument,
)
from app.services.layout_service import generate_layout_options
from app.services.design_review_service import build_local_design_review
from app.services.home_coach_service import build_home_coach_package
from app.services.living_plan_service import build_living_plan_package
from app.services.project_workflow_service import build_project_workflow
from app.services.floorplan_library_service import (
    get_floorplan_template,
    list_dataset_sources,
    search_floorplan_library,
)
from app.services.openai_service import (
    analyze_floorplan_image,
    build_render_prompt,
    generate_interior_image,
    openai_runtime_status,
    parse_design_brief,
    review_design_options,
    reset_request_openai_overrides,
    set_request_openai_overrides,
)
from app.services.input_preparation_service import prepare_floorplan_input
from app.workers.jobs import process_parse_floorplan, run_parse_floorplan_job


async def _openai_request_context(
    x_openai_api_key: Annotated[str | None, Header(alias="X-OpenAI-API-Key")] = None,
    x_openai_model_text: Annotated[str | None, Header(alias="X-OpenAI-Model-Text")] = None,
    x_openai_model_fast: Annotated[str | None, Header(alias="X-OpenAI-Model-Fast")] = None,
    x_openai_model_image: Annotated[str | None, Header(alias="X-OpenAI-Model-Image")] = None,
):
    tokens = set_request_openai_overrides(
        x_openai_api_key,
        x_openai_model_text,
        x_openai_model_fast,
        x_openai_model_image,
    )
    try:
        yield
    finally:
        reset_request_openai_overrides(tokens)


router = APIRouter(dependencies=[Depends(_openai_request_context)])


def _project_or_404(db: Session, project_id: str) -> ProjectModel:
    project = db.get(ProjectModel, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


def _asset_doc(model: AssetModel) -> Asset:
    return Asset(
        id=model.id,
        project_id=model.project_id,
        asset_type=model.asset_type,  # type: ignore[arg-type]
        local_path=model.local_path,
        mime_type=model.mime_type,
        width=model.width,
        height=model.height,
        metadata=model.extra_metadata,
        created_at=model.created_at,
    )


def _floorplan_doc(model: FloorPlanModel) -> FloorPlanDocument:
    return FloorPlanDocument(
        id=model.id,
        project_id=model.project_id,
        created_at=model.created_at,
        **model.data,
    )


def _brief_doc(model: DesignBriefModel) -> DesignBriefDocument:
    return DesignBriefDocument(
        id=model.id,
        project_id=model.project_id,
        source_text=model.source_text,
        created_at=model.created_at,
        **model.data,
    )


def _layout_doc(model: LayoutOptionModel) -> LayoutOptionDocument:
    return LayoutOptionDocument(
        project_id=model.project_id,
        floorplan_id=model.floorplan_id,
        brief_id=model.brief_id,
        created_at=model.created_at,
        **model.data,
    )


def _render_doc(model: RenderAssetModel) -> RenderAssetDocument:
    return RenderAssetDocument(
        id=model.id,
        project_id=model.project_id,
        status=model.status,  # type: ignore[arg-type]
        prompt=model.prompt,
        input_option_id=model.input_option_id,
        output_path=model.output_path,
        disclaimer=model.disclaimer,
        created_at=model.created_at,
    )


def _safe_upload_suffix(content_type: str, filename: str | None) -> str:
    image_suffixes = {
        "image/png": (".png",),
        "image/jpeg": (".jpg", ".jpeg"),
        "image/jpg": (".jpg", ".jpeg"),
        "image/webp": (".webp",),
    }
    if content_type == "application/pdf":
        return ".pdf"
    suffix = Path(filename or "").suffix.lower()
    allowed = image_suffixes.get(content_type, (".png",))
    if suffix in allowed:
        return suffix
    return allowed[0]


@router.get("/settings/openai", response_model=OpenAISettingsStatus)
def get_openai_settings_status() -> OpenAISettingsStatus:
    return OpenAISettingsStatus.model_validate(openai_runtime_status())


@router.get("/floorplan-library", response_model=FloorPlanLibrarySearchResponse)
def search_floorplan_templates(
    query: str | None = Query(default=None, max_length=120),
    bedrooms: int | None = Query(default=None, ge=0, le=8),
    min_area: float | None = Query(default=None, ge=0),
    max_area: float | None = Query(default=None, ge=0),
    dataset: str | None = Query(default=None, max_length=80),
    tags: str | None = Query(default=None, max_length=160),
    limit: int = Query(default=12, ge=1, le=120),
) -> FloorPlanLibrarySearchResponse:
    return FloorPlanLibrarySearchResponse(
        sources=list_dataset_sources(),
        items=search_floorplan_library(
            query=query,
            bedrooms=bedrooms,
            min_area=min_area,
            max_area=max_area,
            dataset=dataset,
            tags=tags,
            limit=limit,
        ),
    )


def _latest_floorplan(db: Session, project_id: str) -> FloorPlanModel:
    floorplan = db.scalars(
        select(FloorPlanModel)
        .where(FloorPlanModel.project_id == project_id)
        .order_by(FloorPlanModel.created_at.desc())
    ).first()
    if floorplan is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No floorplan found. Upload and parse an asset first.",
        )
    return floorplan


def _latest_import_asset(db: Session, project_id: str) -> AssetModel | None:
    return db.scalars(
        select(AssetModel)
        .where(AssetModel.project_id == project_id)
        .where(AssetModel.asset_type.in_(["image", "pdf"]))
        .order_by(AssetModel.created_at.desc())
    ).first()


def _latest_brief(db: Session, project_id: str) -> DesignBriefModel:
    brief = db.scalars(
        select(DesignBriefModel)
        .where(DesignBriefModel.project_id == project_id)
        .order_by(DesignBriefModel.created_at.desc())
    ).first()
    if brief is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No design brief found. Submit a brief before generating layouts.",
        )
    return brief


def _layout_options_for_project(db: Session, project_id: str) -> list[LayoutOptionDocument]:
    option_records = db.scalars(
        select(LayoutOptionModel)
        .where(LayoutOptionModel.project_id == project_id)
        .order_by(LayoutOptionModel.score.desc())
    ).all()
    return [LayoutOptionDocument.model_validate(_layout_doc(record)) for record in option_records]


@router.post("/projects", response_model=Project, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectModel:
    project = ProjectModel(title=payload.title, status="draft")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.post("/demo-project", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
def create_demo_project(db: Session = Depends(get_db)) -> ProjectDetail:
    fixture_dir = ROOT_DIR / "tests" / "fixtures"
    floorplan = FloorPlan.model_validate_json(
        (fixture_dir / "simple_2br_floorplan.json").read_text(encoding="utf-8")
    )
    brief = DesignBrief.model_validate_json(
        (fixture_dir / "sample_design_brief.json").read_text(encoding="utf-8")
    )

    project = ProjectModel(title="示例两居室", status="layout_ready")
    db.add(project)
    db.flush()

    floorplan_record = FloorPlanModel(
        project_id=project.id,
        data=floorplan.model_dump(),
    )
    brief_record = DesignBriefModel(
        project_id=project.id,
        source_text="示例：一家三口，温暖木色，高收纳，需要书柜和亲子活动区。",
        data=brief.model_dump(),
    )
    db.add_all([floorplan_record, brief_record])
    db.flush()

    options = generate_layout_options(floorplan, brief)
    for option in options:
        db.add(
            LayoutOptionModel(
                id=option.id,
                project_id=project.id,
                floorplan_id=floorplan_record.id,
                brief_id=brief_record.id,
                strategy=option.strategy,
                score=option.score,
                data=option.model_dump(),
            )
        )

    db.commit()
    return get_project(project.id, db)


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectDetail:
    project = _project_or_404(db, project_id)
    assets = db.scalars(
        select(AssetModel)
        .where(AssetModel.project_id == project_id)
        .order_by(AssetModel.created_at.asc())
    ).all()
    floorplans = db.scalars(
        select(FloorPlanModel)
        .where(FloorPlanModel.project_id == project_id)
        .order_by(FloorPlanModel.created_at.asc())
    ).all()
    briefs = db.scalars(
        select(DesignBriefModel)
        .where(DesignBriefModel.project_id == project_id)
        .order_by(DesignBriefModel.created_at.asc())
    ).all()
    options = db.scalars(
        select(LayoutOptionModel)
        .where(LayoutOptionModel.project_id == project_id)
        .order_by(LayoutOptionModel.created_at.asc())
    ).all()
    renders = db.scalars(
        select(RenderAssetModel)
        .where(RenderAssetModel.project_id == project_id)
        .order_by(RenderAssetModel.created_at.asc())
    ).all()
    return ProjectDetail(
        id=project.id,
        title=project.title,
        created_at=project.created_at,
        status=project.status,
        assets=[_asset_doc(asset) for asset in assets],
        floorplans=[_floorplan_doc(floorplan) for floorplan in floorplans],
        briefs=[_brief_doc(brief) for brief in briefs],
        layout_options=[_layout_doc(option) for option in options],
        renders=[_render_doc(render) for render in renders],
    )


@router.post("/projects/{project_id}/export", response_model=Asset, status_code=status.HTTP_201_CREATED)
def export_project(project_id: str, db: Session = Depends(get_db)) -> Asset:
    detail = get_project(project_id, db)
    project_dir = get_settings().storage_dir / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"nestcanvas_export_{uuid4().hex[:12]}.json"
    export_payload = detail.model_dump(mode="json")
    if detail.floorplans and detail.briefs and detail.layout_options:
        workflow = build_project_workflow(detail)
        export_payload["workflow"] = workflow.model_dump(mode="json")
        review = build_local_design_review(
            project_id=project_id,
            floorplan=FloorPlan.model_validate(detail.floorplans[-1]),
            layout_options=[LayoutOptionDocument.model_validate(option) for option in detail.layout_options],
            brief=DesignBrief.model_validate(detail.briefs[-1]),
        )
        export_payload["design_review"] = review.model_dump(mode="json")
        living_plan = build_living_plan_package(
            project_id=project_id,
            floorplan=FloorPlan.model_validate(detail.floorplans[-1]),
            layout_options=[LayoutOptionDocument.model_validate(option) for option in detail.layout_options],
            brief=DesignBrief.model_validate(detail.briefs[-1]),
            review=review,
        )
        export_payload["living_plan"] = living_plan.model_dump(mode="json")
        home_coach = build_home_coach_package(
            project_id=project_id,
            workflow=workflow,
            floorplan=FloorPlan.model_validate(detail.floorplans[-1]),
            layout_options=[LayoutOptionDocument.model_validate(option) for option in detail.layout_options],
            brief=DesignBrief.model_validate(detail.briefs[-1]),
            living_plan=living_plan,
            review=review,
        )
        export_payload["home_coach"] = home_coach.model_dump(mode="json")
    path.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    model = AssetModel(
        project_id=project_id,
        asset_type="export",
        local_path=str(path),
        mime_type="application/json",
        width=None,
        height=None,
        extra_metadata={"format": "ProjectDetail", "title": detail.title},
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return _asset_doc(model)


@router.get("/projects/{project_id}/workflow", response_model=ProjectWorkflow)
def get_project_workflow(project_id: str, db: Session = Depends(get_db)) -> ProjectWorkflow:
    detail = get_project(project_id, db)
    return build_project_workflow(detail)


@router.post("/projects/{project_id}/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
def upload_asset(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Asset:
    _project_or_404(db, project_id)

    content_type = file.content_type or "application/octet-stream"
    if content_type not in {"image/png", "image/jpeg", "image/jpg", "image/webp", "application/pdf"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PNG, JPG, WEBP and PDF uploads are supported.",
        )

    asset_type = "pdf" if content_type == "application/pdf" else "image"
    suffix = _safe_upload_suffix(content_type, file.filename)

    project_dir = get_settings().storage_dir / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{uuid4().hex}{suffix}"
    with path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    width: int | None = None
    height: int | None = None
    if asset_type == "image":
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception:
            width = None
            height = None

    model = AssetModel(
        project_id=project_id,
        asset_type=asset_type,
        local_path=str(path),
        mime_type=content_type,
        width=width,
        height=height,
        extra_metadata={"original_filename": file.filename},
    )
    db.add(model)
    project = db.get(ProjectModel, project_id)
    if project is not None:
        project.status = "asset_uploaded"
    db.commit()
    db.refresh(model)
    return _asset_doc(model)


@router.post("/projects/{project_id}/prepare-input", response_model=InputPreparationResult)
def prepare_project_input(project_id: str, db: Session = Depends(get_db)) -> InputPreparationResult:
    project = _project_or_404(db, project_id)
    source_asset = _latest_import_asset(db, project_id)
    if source_asset is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload an image or PDF asset before preparing input.",
        )

    prepared = prepare_floorplan_input(source_asset.local_path, project_id)
    if prepared.output_path is not None:
        vision = analyze_floorplan_image(str(prepared.output_path))
        vision_notes = [str(note) for note in vision.get("notes", []) if note]
        model = AssetModel(
            project_id=project_id,
            asset_type="prepared_image",
            local_path=str(prepared.output_path),
            mime_type="image/png",
            width=prepared.width,
            height=prepared.height,
            extra_metadata={
                "source_asset_id": source_asset.id,
                "quality_score": prepared.quality_score,
                "preparation_stage": prepared.preparation_stage,
                "detected_content": prepared.detected_content,
                "operations": prepared.operations,
                "warnings": prepared.warnings,
                "suggestions": prepared.suggestions,
                "crop_bbox_px": prepared.crop_bbox_px,
                "perspective_corrected": prepared.perspective_corrected,
                "vision_notes": vision_notes,
            },
        )
        db.add(model)
        project.status = "input_prepared"
        db.commit()
        db.refresh(model)
        prepared_asset = _asset_doc(model)
    else:
        vision_notes = []
        prepared_asset = _asset_doc(source_asset)

    return InputPreparationResult(
        project_id=project_id,
        source_asset_id=source_asset.id,
        prepared_asset=prepared_asset,
        quality_score=prepared.quality_score,
        preparation_stage=prepared.preparation_stage,
        detected_content=prepared.detected_content,
        operations=prepared.operations,
        warnings=prepared.warnings,
        suggestions=prepared.suggestions,
        vision_notes=vision_notes,
        crop_bbox_px=prepared.crop_bbox_px,
        perspective_corrected=prepared.perspective_corrected,
    )


@router.post("/projects/{project_id}/starter-floorplan", response_model=FloorPlanDocument)
def create_starter_floorplan(project_id: str, db: Session = Depends(get_db)) -> FloorPlanDocument:
    project = _project_or_404(db, project_id)
    fixture = ROOT_DIR / "tests" / "fixtures" / "simple_2br_floorplan.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    data["confidence"] = min(float(data.get("confidence", 0.5)), 0.48)
    warnings = list(data.get("warnings", []))
    warnings.append("已使用草稿底图启动项目；请在拿到真实照片或户型图后重新上传校正。")
    data["warnings"] = warnings
    floorplan = FloorPlan.model_validate(data)

    model = FloorPlanModel(project_id=project_id, data=floorplan.model_dump())
    db.add(model)
    project.status = "floorplan_draft"
    db.commit()
    db.refresh(model)
    return _floorplan_doc(model)


@router.post(
    "/projects/{project_id}/library-floorplan/{template_id}",
    response_model=FloorPlanDocument,
)
def create_library_floorplan(
    project_id: str, template_id: str, db: Session = Depends(get_db)
) -> FloorPlanDocument:
    project = _project_or_404(db, project_id)
    template = get_floorplan_template(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Floorplan template not found.",
        )

    floorplan = template.floorplan.model_copy(deep=True)
    floorplan.warnings = [
        *floorplan.warnings,
        (
            f"已从户型库选择模板 {template.title}；来源 {template.source_dataset_name}，"
            "交付前请按真实资料校正尺寸和门窗。"
        ),
    ]
    record = FloorPlanModel(project_id=project_id, data=floorplan.model_dump())
    db.add(record)
    project.status = "floorplan_template"
    db.commit()
    db.refresh(record)
    return _floorplan_doc(record)


@router.post("/projects/{project_id}/parse-floorplan", response_model=ParseJobResponse)
def parse_floorplan(project_id: str, db: Session = Depends(get_db)) -> ParseJobResponse:
    _project_or_404(db, project_id)
    asset_exists = db.scalars(
        select(AssetModel)
        .where(AssetModel.project_id == project_id)
        .where(AssetModel.asset_type.in_(["prepared_image", "image", "pdf"]))
    ).first()
    if asset_exists is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload an image or PDF asset before parsing.",
        )

    job = JobModel(project_id=project_id, job_type="parse_floorplan")
    db.add(job)
    db.commit()
    db.refresh(job)

    if get_settings().sync_jobs:
        process_parse_floorplan(db, job.id)
    else:
        try:
            from redis import Redis
            from rq import Queue

            Queue("nestcanvas", connection=Redis.from_url(get_settings().redis_url)).enqueue(
                run_parse_floorplan_job, job.id
            )
        except Exception:
            process_parse_floorplan(db, job.id)

    return ParseJobResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobModel:
    job = db.get(JobModel, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return job


@router.get("/floorplans/{floorplan_id}", response_model=FloorPlanDocument)
def get_floorplan(floorplan_id: str, db: Session = Depends(get_db)) -> FloorPlanDocument:
    floorplan = db.get(FloorPlanModel, floorplan_id)
    if floorplan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found.")
    return _floorplan_doc(floorplan)


@router.patch("/floorplans/{floorplan_id}", response_model=FloorPlanDocument)
def update_floorplan(
    floorplan_id: str,
    payload: FloorPlan,
    db: Session = Depends(get_db),
) -> FloorPlanDocument:
    floorplan = db.get(FloorPlanModel, floorplan_id)
    if floorplan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floorplan not found.")
    floorplan.data = payload.model_dump()
    db.commit()
    db.refresh(floorplan)
    return _floorplan_doc(floorplan)


@router.post("/projects/{project_id}/brief", response_model=DesignBriefDocument)
def create_brief(
    project_id: str,
    payload: BriefRequest,
    db: Session = Depends(get_db),
) -> DesignBriefDocument:
    _project_or_404(db, project_id)
    brief = parse_design_brief(payload.text)
    model = DesignBriefModel(
        project_id=project_id,
        source_text=payload.text,
        data=brief.model_dump(),
    )
    db.add(model)
    project = db.get(ProjectModel, project_id)
    if project is not None:
        project.status = "brief_ready"
    db.commit()
    db.refresh(model)
    return _brief_doc(model)


@router.post("/projects/{project_id}/layout-options", response_model=list[LayoutOptionDocument])
def create_layout_options(
    project_id: str, db: Session = Depends(get_db)
) -> list[LayoutOptionDocument]:
    _project_or_404(db, project_id)
    floorplan_record = _latest_floorplan(db, project_id)
    brief_record = _latest_brief(db, project_id)
    floorplan = FloorPlan.model_validate(floorplan_record.data)
    brief = DesignBrief.model_validate(brief_record.data)

    options = generate_layout_options(floorplan, brief)
    previous_renders = db.scalars(
        select(RenderAssetModel).where(RenderAssetModel.project_id == project_id)
    ).all()
    for render in previous_renders:
        db.delete(render)

    previous_options = db.scalars(
        select(LayoutOptionModel).where(LayoutOptionModel.project_id == project_id)
    ).all()
    for option in previous_options:
        db.delete(option)

    records: list[LayoutOptionModel] = []
    for option in options:
        model = LayoutOptionModel(
            id=option.id,
            project_id=project_id,
            floorplan_id=floorplan_record.id,
            brief_id=brief_record.id,
            strategy=option.strategy,
            score=option.score,
            data=option.model_dump(),
        )
        db.add(model)
        records.append(model)
    project = db.get(ProjectModel, project_id)
    if project is not None:
        project.status = "layout_ready"
    db.commit()
    for record in records:
        db.refresh(record)
    return [_layout_doc(record) for record in records]


@router.post("/projects/{project_id}/design-review", response_model=DesignReview)
def create_design_review(project_id: str, db: Session = Depends(get_db)) -> DesignReview:
    _project_or_404(db, project_id)
    floorplan_record = _latest_floorplan(db, project_id)
    brief_record = _latest_brief(db, project_id)
    option_records = db.scalars(
        select(LayoutOptionModel)
        .where(LayoutOptionModel.project_id == project_id)
        .order_by(LayoutOptionModel.score.desc())
    ).all()
    if not option_records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No layout options found. Generate layout options before reviewing.",
        )

    floorplan = FloorPlan.model_validate(floorplan_record.data)
    brief = DesignBrief.model_validate(brief_record.data)
    options = [LayoutOptionDocument.model_validate(_layout_doc(record)) for record in option_records]
    return review_design_options(project_id, floorplan, options, brief)


@router.post("/projects/{project_id}/living-plan", response_model=LivingPlanPackage)
def create_living_plan(project_id: str, db: Session = Depends(get_db)) -> LivingPlanPackage:
    _project_or_404(db, project_id)
    floorplan_record = _latest_floorplan(db, project_id)
    brief_record = _latest_brief(db, project_id)
    options = _layout_options_for_project(db, project_id)
    if not options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No layout options found. Generate layout options before building a living plan.",
        )

    floorplan = FloorPlan.model_validate(floorplan_record.data)
    brief = DesignBrief.model_validate(brief_record.data)
    review = build_local_design_review(project_id, floorplan, options, brief)
    return build_living_plan_package(project_id, floorplan, options, brief, review=review)


@router.post("/projects/{project_id}/home-coach", response_model=HomeCoachPackage)
def create_home_coach(project_id: str, db: Session = Depends(get_db)) -> HomeCoachPackage:
    detail = get_project(project_id, db)
    if not detail.floorplans or not detail.briefs or not detail.layout_options:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="FloorPlan, DesignBrief and layout options are required before building a Home Coach package.",
        )
    floorplan = FloorPlan.model_validate(detail.floorplans[-1])
    brief = DesignBrief.model_validate(detail.briefs[-1])
    options = [LayoutOptionDocument.model_validate(option) for option in detail.layout_options]
    review = build_local_design_review(project_id, floorplan, options, brief)
    living_plan = build_living_plan_package(project_id, floorplan, options, brief, review=review)
    workflow = build_project_workflow(detail)
    return build_home_coach_package(
        project_id=project_id,
        workflow=workflow,
        floorplan=floorplan,
        brief=brief,
        layout_options=options,
        living_plan=living_plan,
        review=review,
    )


@router.post("/layout-options/{option_id}/render", response_model=RenderAssetDocument)
def render_layout_option(option_id: str, db: Session = Depends(get_db)) -> RenderAssetDocument:
    option_record = db.get(LayoutOptionModel, option_id)
    if option_record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layout option not found.")

    floorplan_record = db.get(FloorPlanModel, option_record.floorplan_id)
    brief_record = db.get(DesignBriefModel, option_record.brief_id)
    if floorplan_record is None or brief_record is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Layout option is missing its floorplan or design brief.",
        )

    floorplan = FloorPlan.model_validate(floorplan_record.data)
    layout_option = _layout_doc(option_record)
    brief = DesignBrief.model_validate(brief_record.data)
    prompt = build_render_prompt(floorplan, layout_option, brief)
    generated = generate_interior_image(prompt)

    model = RenderAssetModel(
        id=generated.id,
        project_id=option_record.project_id,
        option_id=option_record.id,
        status=generated.status,
        prompt=generated.prompt,
        input_option_id=option_record.id,
        output_path=generated.output_path,
        disclaimer=generated.disclaimer,
    )
    db.add(model)
    project = db.get(ProjectModel, option_record.project_id)
    if project is not None:
        project.status = "render_ready"
    db.commit()
    db.refresh(model)
    return _render_doc(model)


@router.get("/projects/{project_id}/renders", response_model=list[RenderAssetDocument])
def list_renders(project_id: str, db: Session = Depends(get_db)) -> list[RenderAssetDocument]:
    _project_or_404(db, project_id)
    renders = db.scalars(
        select(RenderAssetModel)
        .where(RenderAssetModel.project_id == project_id)
        .order_by(RenderAssetModel.created_at.asc())
    ).all()
    return [_render_doc(render) for render in renders]
