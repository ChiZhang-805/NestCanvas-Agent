from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class ProjectModel(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("proj")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)

    assets: Mapped[list[AssetModel]] = relationship(
        "AssetModel", back_populates="project", cascade="all, delete-orphan"
    )
    floorplans: Mapped[list[FloorPlanModel]] = relationship(
        "FloorPlanModel", back_populates="project", cascade="all, delete-orphan"
    )
    briefs: Mapped[list[DesignBriefModel]] = relationship(
        "DesignBriefModel", back_populates="project", cascade="all, delete-orphan"
    )
    layout_options: Mapped[list[LayoutOptionModel]] = relationship(
        "LayoutOptionModel", back_populates="project", cascade="all, delete-orphan"
    )
    renders: Mapped[list[RenderAssetModel]] = relationship(
        "RenderAssetModel", back_populates="project", cascade="all, delete-orphan"
    )


class AssetModel(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("asset")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    local_path: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(120), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    project: Mapped[ProjectModel] = relationship("ProjectModel", back_populates="assets")


class FloorPlanModel(TimestampMixin, Base):
    __tablename__ = "floorplans"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("floor")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped[ProjectModel] = relationship(
        "ProjectModel", back_populates="floorplans"
    )


class DesignBriefModel(TimestampMixin, Base):
    __tablename__ = "design_briefs"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("brief")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped[ProjectModel] = relationship("ProjectModel", back_populates="briefs")


class LayoutOptionModel(TimestampMixin, Base):
    __tablename__ = "layout_options"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("option")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    floorplan_id: Mapped[str] = mapped_column(ForeignKey("floorplans.id"), nullable=False)
    brief_id: Mapped[str] = mapped_column(ForeignKey("design_briefs.id"), nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)

    project: Mapped[ProjectModel] = relationship(
        "ProjectModel", back_populates="layout_options"
    )


class RenderAssetModel(TimestampMixin, Base):
    __tablename__ = "render_assets"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("render")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    option_id: Mapped[str] = mapped_column(ForeignKey("layout_options.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    input_option_id: Mapped[str] = mapped_column(String(64), nullable=False)
    output_path: Mapped[str] = mapped_column(Text, nullable=False)
    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)

    project: Mapped[ProjectModel] = relationship("ProjectModel", back_populates="renders")


class JobModel(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: new_id("job")
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="queued", nullable=False)
    stage: Mapped[str] = mapped_column(String(100), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
