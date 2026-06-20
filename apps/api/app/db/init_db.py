from app.db.base import Base
from app.db.session import engine

# Import models so SQLAlchemy sees them before create_all.
from app.models.entities import (  # noqa: F401
    AssetModel,
    DesignBriefModel,
    FloorPlanModel,
    JobModel,
    LayoutOptionModel,
    ProjectModel,
    RenderAssetModel,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
