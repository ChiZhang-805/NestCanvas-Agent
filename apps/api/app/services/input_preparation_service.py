from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import uuid4

from PIL import Image, ImageOps

from app.core.config import get_settings


@dataclass
class PreparedInput:
    output_path: Path | None
    width: int | None
    height: int | None
    quality_score: float
    preparation_stage: Literal["prepared", "passthrough"]
    detected_content: Literal["floorplan_like", "document_like", "unknown"]
    operations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    crop_bbox_px: list[int] | None = None
    perspective_corrected: bool = False


def _order_quad_points(points):
    import numpy as np

    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[sums.argmin()]
    rect[2] = points[sums.argmax()]
    rect[1] = points[diffs.argmin()]
    rect[3] = points[diffs.argmax()]
    return rect


def _resize_for_processing(image):
    height, width = image.shape[:2]
    longest = max(width, height)
    if longest <= 2600:
        return image, 1.0
    scale = 2600 / longest
    import cv2  # type: ignore

    resized = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)
    return resized, scale


def _find_document_quad(image):
    import cv2  # type: ignore

    height, width = image.shape[:2]
    area = float(width * height)
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    edges = cv2.dilate(edges, kernel, iterations=1)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_quad = None
    best_area = 0.0
    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.025 * perimeter, True)
        contour_area = cv2.contourArea(approx)
        if len(approx) == 4 and contour_area > best_area and contour_area > area * 0.12:
            best_quad = approx.reshape(4, 2).astype("float32")
            best_area = float(contour_area)
    return best_quad, best_area / area if area else 0.0


def _find_content_bbox(image) -> tuple[int, int, int, int] | None:
    import cv2  # type: ignore

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        35,
        9,
    )
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    threshold = cv2.morphologyEx(threshold, cv2.MORPH_CLOSE, kernel, iterations=1)
    points = cv2.findNonZero(threshold)
    if points is None:
        return None

    x, y, w, h = cv2.boundingRect(points)
    if w * h < width * height * 0.06:
        return None

    margin_x = int(width * 0.025)
    margin_y = int(height * 0.025)
    left = max(0, x - margin_x)
    top = max(0, y - margin_y)
    right = min(width, x + w + margin_x)
    bottom = min(height, y + h + margin_y)
    return left, top, right, bottom


def _warp_quad(image, quad):
    import cv2  # type: ignore
    import numpy as np

    rect = _order_quad_points(quad)
    tl, tr, br, bl = rect
    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_width = max(int(width_a), int(width_b), 1)
    max_height = max(int(height_a), int(height_b), 1)
    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def _enhance_floorplan_image(image):
    import cv2  # type: ignore

    lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lightness = clahe.apply(lightness)
    enhanced = cv2.cvtColor(cv2.merge((lightness, a_channel, b_channel)), cv2.COLOR_LAB2RGB)
    blurred = cv2.GaussianBlur(enhanced, (0, 0), 1.15)
    sharpened = cv2.addWeighted(enhanced, 1.3, blurred, -0.3, 0)
    return sharpened


def _quality_report(
    image, coverage_ratio: float, perspective_corrected: bool
) -> tuple[float, list[str], list[str], Literal["floorplan_like", "document_like", "unknown"]]:
    import cv2  # type: ignore

    height, width = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast = float(gray.std())
    min_side = min(width, height)

    resolution_score = min(min_side / 1000, 1.0) * 34
    sharpness_score = min(laplacian_var / 260, 1.0) * 24
    contrast_score = min(contrast / 58, 1.0) * 18
    coverage_score = min(max(coverage_ratio, 0.18) / 0.72, 1.0) * 14
    geometry_score = 10 if perspective_corrected else 6
    score = round(resolution_score + sharpness_score + contrast_score + coverage_score + geometry_score, 1)

    warnings: list[str] = []
    suggestions: list[str] = []
    if min_side < 900:
        warnings.append("图像分辨率偏低，细小尺寸和门窗符号可能不稳定。")
        suggestions.append("尽量使用原图、手机主摄或更近距离重拍。")
    if laplacian_var < 75:
        warnings.append("图像有明显模糊，线条识别可信度会下降。")
        suggestions.append("拍照时让手机与纸面平行，并等待自动对焦完成。")
    if coverage_ratio < 0.28:
        warnings.append("户型内容占画面比例偏小，背景信息仍然较多。")
        suggestions.append("让户型图尽量占满取景框，少拍桌面、手指和册子边框。")
    if contrast < 34:
        warnings.append("线条对比度偏低，已做增强但仍建议确认墙体边界。")
        suggestions.append("避免反光和阴影，选择均匀光线下重新拍摄。")

    if score >= 72:
        detected_content = "floorplan_like"
    elif score >= 50:
        detected_content = "document_like"
    else:
        detected_content = "unknown"

    return min(score, 100.0), warnings, suggestions, detected_content


def _pil_fallback_prepare(source_path: Path, project_id: str) -> PreparedInput:
    output_dir = get_settings().storage_dir / "projects" / project_id / "prepared"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"prepared_{uuid4().hex[:12]}.png"
    with Image.open(source_path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = ImageOps.autocontrast(image)
        image.save(output_path, format="PNG")
        width, height = image.size
    return PreparedInput(
        output_path=output_path,
        width=width,
        height=height,
        quality_score=52.0,
        preparation_stage="prepared",
        detected_content="unknown",
        operations=["exif_orient", "autocontrast"],
        warnings=["OpenCV 预处理不可用，已使用基础图片增强。"],
        suggestions=["建议在校正页人工确认比例尺、房间边界和门窗位置。"],
    )


def prepare_floorplan_input(source_path: str, project_id: str) -> PreparedInput:
    path = Path(source_path)
    if path.suffix.lower() == ".pdf":
        return PreparedInput(
            output_path=None,
            width=None,
            height=None,
            quality_score=58.0,
            preparation_stage="passthrough",
            detected_content="document_like",
            operations=["pdf_passthrough"],
            warnings=["PDF 暂不做图片清理，会直接进入户型解析。"],
            suggestions=["如果 PDF 来自拍照扫描，建议另存为清晰图片后再上传。"],
        )

    try:
        import cv2  # type: ignore
        import numpy as np
    except Exception:
        return _pil_fallback_prepare(path, project_id)

    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        original_width, original_height = image.size
        source = np.array(image)

    working, scale = _resize_for_processing(source)
    operations = ["exif_orient"]
    warnings: list[str] = []
    suggestions: list[str] = []
    crop_bbox_px: list[int] | None = None
    perspective_corrected = False
    coverage_ratio = 1.0

    quad, quad_coverage = _find_document_quad(working)
    if quad is not None:
        working = _warp_quad(working, quad)
        perspective_corrected = True
        coverage_ratio = quad_coverage
        operations.append("perspective_rectify")
    else:
        bbox = _find_content_bbox(working)
        if bbox is not None:
            left, top, right, bottom = bbox
            coverage_ratio = ((right - left) * (bottom - top)) / float(working.shape[0] * working.shape[1])
            crop_bbox_px = [
                int(left / scale),
                int(top / scale),
                int(right / scale),
                int(bottom / scale),
            ]
            working = working[top:bottom, left:right]
            operations.append("content_crop")
        else:
            warnings.append("没有识别到稳定的纸张边界，已保留整张图。")
            suggestions.append("如果画面里有售楼册文字、桌面或手指，建议让户型图区域更完整地占满画面。")

    enhanced = _enhance_floorplan_image(working)
    operations.append("contrast_enhance")
    operations.append("line_sharpen")

    quality_score, quality_warnings, quality_suggestions, detected_content = _quality_report(
        enhanced, coverage_ratio, perspective_corrected
    )
    warnings.extend(quality_warnings)
    suggestions.extend(quality_suggestions)

    output_dir = get_settings().storage_dir / "projects" / project_id / "prepared"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"prepared_{uuid4().hex[:12]}.png"
    cv2.imwrite(str(output_path), cv2.cvtColor(enhanced, cv2.COLOR_RGB2BGR))
    height, width = enhanced.shape[:2]

    if max(original_width, original_height) > 2600:
        operations.append("downscale_for_processing")

    return PreparedInput(
        output_path=output_path,
        width=int(width),
        height=int(height),
        quality_score=quality_score,
        preparation_stage="prepared",
        detected_content=detected_content,
        operations=operations,
        warnings=warnings[:6],
        suggestions=list(dict.fromkeys(suggestions))[:6],
        crop_bbox_px=crop_bbox_px,
        perspective_corrected=perspective_corrected,
    )
