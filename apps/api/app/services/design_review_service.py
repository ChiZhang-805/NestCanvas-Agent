from __future__ import annotations

from statistics import mean
from typing import Literal

from app.schemas.domain import DesignBrief, DesignReview, FloorPlan, LayoutOption, LayoutOptionReview


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def _has_category(option: LayoutOption, categories: set[str]) -> bool:
    return any(item.category in categories for item in option.furniture_items)


def _storage_score(option: LayoutOption, brief: DesignBrief) -> float:
    storage_units = float(option.metrics.get("storage_units", 0))
    target = 4 if brief.storage_level == "high" else 2 if brief.storage_level == "medium" else 1
    return _clamp_score(48 + min(storage_units / target, 1.6) * 38)


def _circulation_score(option: LayoutOption) -> float:
    return _clamp_score(100 - len(option.hard_errors) * 32 - len(option.soft_warnings) * 6)


def _lifestyle_fit_score(option: LayoutOption, brief: DesignBrief) -> float:
    score = 62.0
    must_have = set(brief.must_have)
    residents = set(brief.residents)

    if "large_bookshelf" in must_have:
        score += 16 if _has_category(option, {"bookshelf"}) else -12
    if "more_storage" in must_have:
        score += min(float(option.metrics.get("storage_units", 0)) * 6, 18)
    if "work_from_home_desk" in must_have:
        score += 10 if _has_category(option, {"desk", "work_desk"}) else -8
    if "child" in residents:
        score += 14 if _has_category(option, {"toy_storage"}) else -6
    if brief.budget_cny and brief.budget_cny < 120000:
        score -= max(0, len(option.furniture_items) - 10) * 2

    return _clamp_score(score)


def _risk_score(option: LayoutOption) -> float:
    return _clamp_score(100 - len(option.hard_errors) * 35 - len(option.soft_warnings) * 7)


def _headline(strategy: str, scores: dict[str, float]) -> str:
    if strategy == "open_living":
        return "更开阔，适合喜欢留白和灵活动线的生活方式"
    if strategy == "family_friendly":
        return "更照顾亲子活动和安全通道，适合家庭长期居住"
    if scores["storage"] >= 78:
        return "收纳和日常起居比较均衡，是稳妥的默认方案"
    return "整体可用，但需要进一步校正细节"


def _strengths(option: LayoutOption, scores: dict[str, float], brief: DesignBrief) -> list[str]:
    strengths: list[str] = []
    if scores["circulation"] >= 80:
        strengths.append("硬错误少，家具之间和门口区域的风险较低。")
    if scores["storage"] >= 78:
        strengths.append("收纳单元数量满足当前 brief 的储物强度。")
    if scores["lifestyle_fit"] >= 78:
        strengths.append("家具类型和生活方式关键词匹配度较高。")
    if option.strategy == "open_living":
        strengths.append("客餐厅家具更克制，便于保留活动区和临时布置。")
    if option.strategy == "family_friendly" and "child" in brief.residents:
        strengths.append("加入了亲子收纳元素，更适合有孩子的家庭。")
    return strengths[:4] or ["空间已完成基础家具占位，可进入人工微调。"]


def _concerns(option: LayoutOption, scores: dict[str, float], brief: DesignBrief) -> list[str]:
    concerns: list[str] = []
    if option.hard_errors:
        concerns.append(f"存在 {len(option.hard_errors)} 个硬错误，需要先处理碰撞或挡门问题。")
    if option.soft_warnings:
        concerns.append(f"存在 {len(option.soft_warnings)} 个软风险，建议检查通道宽度和家具贴墙距离。")
    if brief.storage_level == "high" and scores["storage"] < 72:
        concerns.append("当前收纳强度偏低，可能无法承接高收纳需求。")
    if "work_from_home_desk" in brief.must_have and not _has_category(option, {"desk", "work_desk"}):
        concerns.append("brief 提到办公需求，但当前方案还没有明确办公位。")
    if "large_bookshelf" in brief.must_have and not _has_category(option, {"bookshelf"}):
        concerns.append("brief 提到书柜，但当前方案没有书柜占位。")
    return concerns[:4]


def _suggestions(option: LayoutOption, scores: dict[str, float], brief: DesignBrief) -> list[str]:
    suggestions: list[str] = []
    if scores["circulation"] < 78:
        suggestions.append("优先移动或缩小产生风险的家具，再进入渲染。")
    if scores["storage"] < 76 and brief.storage_level in {"medium", "high"}:
        suggestions.append("可在卧室或客厅非窗侧补充高柜、矮柜或整墙收纳。")
    if option.strategy == "open_living":
        suggestions.append("渲染时可以突出自然光、留白和可移动家具。")
    if option.strategy == "balanced_storage":
        suggestions.append("适合作为主推方案，可继续细化柜体尺寸和开门方向。")
    if option.strategy == "family_friendly":
        suggestions.append("建议把尖角家具替换为圆角材质，并检查儿童活动区旁的通道。")
    return suggestions[:4] or ["下一步建议补充预算、材质偏好和是否保留现有家具。"]


def _next_questions(brief: DesignBrief) -> list[str]:
    questions: list[str] = []
    if brief.budget_cny is None:
        questions.append("本次方案的预算上限是多少？")
    if not brief.residents:
        questions.append("常住人数、年龄结构和是否有宠物？")
    if not brief.color_palette:
        questions.append("更偏好暖木、奶油、黑白灰，还是更鲜明的色彩？")
    if not brief.constraints:
        questions.append("哪些墙体、门洞、管线或现有家具必须保留？")
    if "work_from_home_desk" not in brief.must_have:
        questions.append("是否需要独立办公位或临时学习区？")
    return questions[:4]


def build_local_design_review(
    project_id: str,
    floorplan: FloorPlan,
    layout_options: list[LayoutOption],
    brief: DesignBrief,
    generated_with: Literal["local_rules", "openai", "mock"] = "local_rules",
) -> DesignReview:
    option_reviews: list[LayoutOptionReview] = []
    composite_scores: dict[str, float] = {}

    for option in layout_options:
        scores = {
            "storage": _storage_score(option, brief),
            "circulation": _circulation_score(option),
            "lifestyle_fit": _lifestyle_fit_score(option, brief),
            "risk_control": _risk_score(option),
            "layout_engine": round(option.score, 1),
        }
        composite = _clamp_score(mean(scores.values()))
        composite_scores[option.id] = composite
        option_reviews.append(
            LayoutOptionReview(
                option_id=option.id,
                strategy=option.strategy,
                headline=_headline(option.strategy, scores),
                scores={**scores, "composite": composite},
                strengths=_strengths(option, scores, brief),
                concerns=_concerns(option, scores, brief),
                suggestions=_suggestions(option, scores, brief),
            )
        )

    best_option_id = (
        max(composite_scores, key=lambda option_id: composite_scores[option_id])
        if composite_scores
        else None
    )
    best_score = composite_scores.get(best_option_id, 0.0) if best_option_id else 0.0
    readiness = _clamp_score(best_score * 0.72 + floorplan.confidence * 100 * 0.28)

    global_risks = list(floorplan.warnings)
    if floorplan.confidence < 0.75:
        global_risks.append("户型解析置信度仍偏低，建议在进入最终渲染前确认比例尺、门窗和房间类型。")
    if any(option.hard_errors for option in layout_options):
        global_risks.append("至少一套方案存在硬错误，不能直接作为推荐方案交付。")
    if not floorplan.windows:
        global_risks.append("当前 FloorPlan 缺少窗户信息，采光和家具避窗判断会偏弱。")

    if best_option_id:
        best_review = next(review for review in option_reviews if review.option_id == best_option_id)
        summary = (
            f"当前最适合作为主推方向的是 {best_review.strategy}：{best_review.headline}。"
            f"整体落地准备度约 {readiness:.1f}/100。"
        )
    else:
        summary = "当前还没有可评审的布局方案，请先生成方案。"

    return DesignReview(
        project_id=project_id,
        generated_with=generated_with,
        summary=summary,
        best_option_id=best_option_id,
        readiness_score=readiness,
        global_risks=global_risks[:6],
        next_questions=_next_questions(brief),
        option_reviews=option_reviews,
    )
