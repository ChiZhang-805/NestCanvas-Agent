from __future__ import annotations

import base64
import mimetypes
from contextvars import ContextVar, Token
from pathlib import Path
from typing import Literal
from uuid import uuid4

from app.core.config import get_settings
from app.schemas.domain import DesignBrief, DesignReview, FloorPlan, LayoutOption, RenderAsset
from app.services.design_review_service import build_local_design_review
from app.services.render_prompt_service import summarize_layout_for_prompt


DISCLAIMER = "概念效果图仅用于灵感展示，尺寸和可施工性以平面图校正结果为准。"
_request_openai_api_key: ContextVar[str | None] = ContextVar(
    "request_openai_api_key", default=None
)


def set_request_openai_api_key(api_key: str | None) -> Token[str | None]:
    cleaned = api_key.strip() if api_key else None
    return _request_openai_api_key.set(cleaned or None)


def reset_request_openai_api_key(token: Token[str | None]) -> None:
    _request_openai_api_key.reset(token)


def _api_key() -> str | None:
    return _request_openai_api_key.get() or get_settings().openai_api_key


def _has_key() -> bool:
    return bool(_api_key())


def openai_runtime_status() -> dict[str, object]:
    settings = get_settings()
    request_key = _request_openai_api_key.get()
    source = "browser" if request_key else "env" if settings.openai_api_key else "mock"
    return {
        "active": bool(request_key or settings.openai_api_key),
        "source": source,
        "env_key_configured": bool(settings.openai_api_key),
        "request_key_configured": bool(request_key),
        "text_model": settings.openai_model_text,
        "fast_model": settings.openai_model_fast,
        "image_model": settings.openai_image_model,
    }


def analyze_floorplan_image(image_path: str) -> dict:
    if not _has_key():
        return {
            "detected_labels": [],
            "notes": ["mock vision hints: no OPENAI_API_KEY configured"],
            "source": image_path,
        }

    try:
        from openai import OpenAI

        client = OpenAI(api_key=_api_key())
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
        mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
        response = client.responses.create(
            model=get_settings().openai_model_fast,
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Extract room labels, scale notes, doors and windows from this floorplan image. Return concise JSON-like notes.",
                        },
                        {
                            "type": "input_image",
                            "image_url": f"data:{mime_type};base64,{encoded}",
                        },
                    ],
                }
            ],
        )
        return {"notes": [getattr(response, "output_text", "")], "source": image_path}
    except Exception as exc:
        return {
            "detected_labels": [],
            "notes": [f"vision fallback after error: {exc.__class__.__name__}"],
            "source": image_path,
        }


def _mock_design_brief(user_text: str) -> DesignBrief:
    text = user_text.lower()
    residents: list[str] = []
    must_have: list[str] = []
    avoid: list[str] = []
    constraints: list[str] = ["keep existing walls", "do not block balcony door"]

    if any(token in text for token in ["孩子", "child", "kid", "family", "家庭", "一家三口"]):
        residents.extend(["couple", "child"])
    elif any(token in text for token in ["独居", "single", "solo"]):
        residents.append("single_adult")
    else:
        residents.append("couple")

    if any(token in text for token in ["书", "book", "bookshelf", "阅读"]):
        must_have.append("large_bookshelf")
    if any(token in text for token in ["收纳", "storage", "closet", "衣帽间"]):
        must_have.append("more_storage")
    if any(token in text for token in ["办公", "work", "study", "书房"]):
        must_have.append("work_from_home_desk")
    if any(token in text for token in ["暗", "dark", "黑"]):
        avoid.append("dark_palette")
    if any(token in text for token in ["豪华", "luxury"]):
        avoid.append("heavy_luxury")

    storage_level: Literal["high", "medium"] = (
        "high" if ("收纳" in text or "storage" in text or "closet" in text) else "medium"
    )
    style = "warm_wood_minimal"
    if any(token in text for token in ["奶油", "cream"]):
        style = "soft_warm_modern"
    if any(token in text for token in ["日式", "japanese", "muji"]):
        style = "japanese_wood_minimal"

    return DesignBrief(
        style=style,
        budget_cny=200000 if any(token in text for token in ["预算", "budget", "20万", "200000"]) else None,
        residents=residents,
        room_priorities=["living_room", "master_bedroom"],
        must_have=must_have or ["comfortable_living_room"],
        avoid=avoid or ["blocked_circulation"],
        storage_level=storage_level,
        color_palette=["warm white", "oak", "linen"],
        constraints=constraints,
    )


def parse_design_brief(user_text: str) -> DesignBrief:
    if not _has_key():
        return _mock_design_brief(user_text)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=_api_key())
        response = client.responses.parse(
            model=get_settings().openai_model_text,
            input=[
                {
                    "role": "system",
                    "content": "Extract a home design brief. Return only data that fits the provided schema.",
                },
                {"role": "user", "content": user_text},
            ],
            text_format=DesignBrief,
        )
        parsed = response.output_parsed
        if isinstance(parsed, DesignBrief):
            return parsed
    except Exception:
        pass
    return _mock_design_brief(user_text)


def build_render_prompt(
    floorplan: FloorPlan, layout_option: LayoutOption, design_brief: DesignBrief
) -> str:
    summary = summarize_layout_for_prompt(floorplan, layout_option, design_brief)
    return (
        "Create a single inspirational interior concept image for a residential apartment. "
        f"Respect this verified 2D layout summary: {summary}. "
        f"Use style {design_brief.style}, palette {', '.join(design_brief.color_palette)}. "
        "Do not imply structural demolition or construction certainty. "
        "Show warm natural light, realistic furniture scale, and a lived-in but tidy home."
    )


def review_design_options(
    project_id: str,
    floorplan: FloorPlan,
    layout_options: list[LayoutOption],
    design_brief: DesignBrief,
) -> DesignReview:
    local_review = build_local_design_review(
        project_id=project_id,
        floorplan=floorplan,
        layout_options=layout_options,
        brief=design_brief,
        generated_with="mock" if not _has_key() else "local_rules",
    )
    if not _has_key():
        return local_review

    try:
        from openai import OpenAI

        client = OpenAI(api_key=_api_key())
        option_ids = {option.id for option in layout_options}
        response = client.responses.parse(
            model=get_settings().openai_model_text,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are an interior design reviewer for NestCanvas. "
                        "Use only the provided verified geometry and local-rule findings. "
                        "Do not invent furniture coordinates, demolition, construction certainty, or safety claims. "
                        "Preserve exact option_id values. Respond in concise Chinese."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Improve this structured design review while preserving all option ids and numeric scores. "
                        f"Floorplan confidence: {floorplan.confidence}. "
                        f"Rooms: {[room.room_type for room in floorplan.rooms]}. "
                        f"Design brief: {design_brief.model_dump_json()}. "
                        f"Local review: {local_review.model_dump_json()}."
                    ),
                },
            ],
            text_format=DesignReview,
        )
        parsed = response.output_parsed
        if isinstance(parsed, DesignReview):
            parsed_ids = {review.option_id for review in parsed.option_reviews}
            if parsed.best_option_id and parsed.best_option_id not in option_ids:
                return local_review
            if parsed_ids != option_ids:
                return local_review
            return parsed.model_copy(update={"generated_with": "openai", "project_id": project_id})
    except Exception:
        return local_review

    return local_review


def _write_mock_svg(prompt: str) -> Path:
    settings = get_settings()
    render_dir = settings.storage_dir / "renders"
    render_dir.mkdir(parents=True, exist_ok=True)
    path = render_dir / f"mock_render_{uuid4().hex[:12]}.svg"
    safe_prompt = prompt[:220].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="800" viewBox="0 0 1200 800">
  <rect width="1200" height="800" fill="#f7f4ee"/>
  <rect x="80" y="80" width="1040" height="640" rx="18" fill="#fffaf1" stroke="#2f3a35" stroke-width="10"/>
  <rect x="135" y="135" width="420" height="250" fill="#d8e8de" stroke="#2f3a35" stroke-width="5"/>
  <rect x="610" y="135" width="360" height="210" fill="#ead7bd" stroke="#2f3a35" stroke-width="5"/>
  <rect x="150" y="455" width="360" height="185" fill="#f0d4ca" stroke="#2f3a35" stroke-width="5"/>
  <rect x="590" y="420" width="430" height="220" fill="#dfe5ef" stroke="#2f3a35" stroke-width="5"/>
  <rect x="210" y="210" width="220" height="70" rx="16" fill="#506f66"/>
  <rect x="680" y="220" width="180" height="90" rx="45" fill="#8f6548"/>
  <rect x="245" y="505" width="150" height="95" rx="18" fill="#51617a"/>
  <text x="120" y="735" fill="#2f3a35" font-family="Arial, sans-serif" font-size="28">NestCanvas Agent mock concept render</text>
  <text x="120" y="770" fill="#6b6258" font-family="Arial, sans-serif" font-size="20">{safe_prompt}</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    return path


def generate_interior_image(
    prompt: str, reference_image_path: str | None = None
) -> RenderAsset:
    if not _has_key():
        output_path = _write_mock_svg(prompt)
        return RenderAsset(
            id=f"render_{uuid4().hex[:12]}",
            status="completed",
            prompt=prompt,
            input_option_id="pending",
            output_path=str(output_path),
            disclaimer=DISCLAIMER,
        )

    try:
        from openai import OpenAI

        client = OpenAI(api_key=_api_key())
        result = client.images.generate(
            model=get_settings().openai_image_model,
            prompt=prompt,
            size="1536x1024",
            quality="high",
            output_format="png",
            response_format="b64_json",
        )
        image_data = result.data[0].b64_json
        if image_data is None:
            raise ValueError("Image API returned no b64_json data.")
        render_dir = get_settings().storage_dir / "renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        path = render_dir / f"render_{uuid4().hex[:12]}.png"
        path.write_bytes(base64.b64decode(image_data))
        return RenderAsset(
            id=f"render_{uuid4().hex[:12]}",
            status="completed",
            prompt=prompt,
            input_option_id="pending",
            output_path=str(path),
            disclaimer=DISCLAIMER,
        )
    except Exception:
        output_path = _write_mock_svg(prompt)
        return RenderAsset(
            id=f"render_{uuid4().hex[:12]}",
            status="completed",
            prompt=prompt,
            input_option_id="pending",
            output_path=str(output_path),
            disclaimer=DISCLAIMER,
        )
