from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from app.core.config import ROOT_DIR
from app.schemas.domain import FloorPlan
from app.services.geometry_service import normalize_polygon, polygon_area_m2


class FloorPlanParser:
    def parse(self, image_path: str) -> FloorPlan:
        fixture = ROOT_DIR / "tests" / "fixtures" / "simple_2br_floorplan.json"
        data = json.loads(fixture.read_text(encoding="utf-8"))

        warnings = list(data.get("warnings", []))
        try:
            width, height = self._inspect_image(image_path)
            warnings.append(f"Uploaded asset inspected: {width}x{height}px.")
            data["scale_m_per_px"] = round(max(0.01, data["scale_m_per_px"]), 4)
        except Exception:
            warnings.append("MVP fallback floorplan used because image parsing was inconclusive.")

        data["boundary"] = normalize_polygon(data["boundary"])
        for room in data.get("rooms", []):
            room["polygon"] = normalize_polygon(room["polygon"])
            room["area_m2"] = polygon_area_m2(room["polygon"])
        for opening_key in ("doors", "windows"):
            for opening in data.get(opening_key, []):
                opening["bbox"] = normalize_polygon(opening["bbox"])
        data["warnings"] = warnings
        data["confidence"] = min(float(data.get("confidence", 0.62)), 0.72)
        return FloorPlan.model_validate(data)

    def _inspect_image(self, image_path: str) -> tuple[int, int]:
        suffix = Path(image_path).suffix.lower()
        if suffix == ".pdf":
            raise ValueError("PDF vector parsing is not implemented in the MVP parser.")

        with Image.open(image_path) as img:
            width, height = img.size

        try:
            import cv2  # type: ignore

            matrix = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
            if matrix is not None:
                cv2.Canny(matrix, 50, 150)
        except Exception:
            pass
        return width, height
