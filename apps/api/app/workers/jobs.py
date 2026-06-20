from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import AssetModel, FloorPlanModel, JobModel, ProjectModel
from app.services.floorplan_parser import FloorPlanParser


def process_parse_floorplan(db: Session, job_id: str) -> None:
    job = db.get(JobModel, job_id)
    if job is None:
        return

    try:
        job.status = "running"
        job.stage = "loading_asset"
        job.progress = 15
        db.commit()

        asset = db.scalars(
            select(AssetModel)
            .where(AssetModel.project_id == job.project_id)
            .where(AssetModel.asset_type.in_(["prepared_image", "image", "pdf"]))
            .order_by(AssetModel.created_at.desc())
        ).first()
        if asset is None:
            raise ValueError("No uploaded image or PDF asset found for this project.")

        job.stage = "opencv_fallback_parse"
        job.progress = 55
        db.commit()

        floorplan = FloorPlanParser().parse(asset.local_path)
        record = FloorPlanModel(project_id=job.project_id, data=floorplan.model_dump())
        db.add(record)

        project = db.get(ProjectModel, job.project_id)
        if project is not None:
            project.status = "floorplan_parsed"

        db.flush()
        job.status = "completed"
        job.stage = "completed"
        job.progress = 100
        job.result_id = record.id
        job.error = None
        db.commit()
    except Exception as exc:
        job.status = "failed"
        job.stage = "failed"
        job.progress = 100
        job.error = str(exc)
        db.commit()


def run_parse_floorplan_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        process_parse_floorplan(db, job_id)
    finally:
        db.close()
