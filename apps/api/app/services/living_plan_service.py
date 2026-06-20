from __future__ import annotations

from collections import defaultdict
from math import ceil
from typing import Literal

from app.schemas.domain import (
    DesignBrief,
    DesignReview,
    FloorPlan,
    LayoutOption,
    LivingBudgetPhase,
    LivingDiscussionCard,
    LivingPlanPackage,
    LivingShoppingItem,
)


CATEGORY_LABELS = {
    "bed": "床",
    "bookshelf": "书柜",
    "coffee_table": "茶几",
    "counter": "厨房操作台",
    "dining_table": "餐桌",
    "low_drawer": "矮柜",
    "nightstand": "床头柜",
    "sofa": "沙发",
    "toilet": "坐便器",
    "toy_storage": "儿童收纳",
    "tv_console": "电视柜",
    "vanity": "浴室柜",
    "wardrobe": "衣柜",
}

CATEGORY_ESTIMATES = {
    "bed": (2800, 9000),
    "bookshelf": (3500, 14000),
    "coffee_table": (900, 3200),
    "counter": (6000, 24000),
    "dining_table": (1800, 6800),
    "low_drawer": (1200, 4200),
    "nightstand": (500, 1800),
    "sofa": (3500, 16000),
    "toilet": (1200, 4200),
    "toy_storage": (800, 3600),
    "tv_console": (1600, 6800),
    "vanity": (2000, 9000),
    "wardrobe": (4800, 22000),
}

ESSENTIAL_CATEGORIES = {"bed", "sofa", "wardrobe", "counter", "toilet", "vanity"}
COMFORT_CATEGORIES = {"dining_table", "bookshelf", "toy_storage", "tv_console"}
STYLE_CATEGORIES = {"coffee_table", "nightstand", "low_drawer"}
REUSE_FRIENDLY_CATEGORIES = {"coffee_table", "dining_table", "nightstand", "tv_console"}
STORAGE_CATEGORIES = {"wardrobe", "bookshelf", "toy_storage", "low_drawer", "tv_console"}

LivingPriority = Literal["must_buy", "reuse_or_buy", "optional"]
LivingBudgetPhaseKey = Literal["move_in_essentials", "comfort_upgrade", "style_finish", "optional_later"]
LivingBudgetFit = Literal["within_budget", "tight", "over_budget", "unknown"]


def _room_type_by_id(floorplan: FloorPlan) -> dict[str, str]:
    return {room.id: room.room_type for room in floorplan.rooms}


def _select_option(options: list[LayoutOption], review: DesignReview | None) -> LayoutOption:
    if not options:
        raise ValueError("At least one layout option is required.")
    if review and review.best_option_id:
        for option in options:
            if option.id == review.best_option_id:
                return option
    return max(options, key=lambda option: option.score)


def _household_summary(brief: DesignBrief, floorplan: FloorPlan) -> str:
    room_count = len(floorplan.rooms)
    bedroom_count = sum(1 for room in floorplan.rooms if "bedroom" in room.room_type)
    residents = "、".join(brief.residents) if brief.residents else "未填写常住人"
    must_have = "、".join(brief.must_have[:3]) if brief.must_have else "基础居住功能"
    return f"{residents}；{bedroom_count} 间卧室、{room_count} 个空间；本轮优先满足 {must_have}。"


def _priority_for(category: str, brief: DesignBrief) -> LivingPriority:
    if category in ESSENTIAL_CATEGORIES:
        return "must_buy"
    if category in STORAGE_CATEGORIES and brief.storage_level == "high":
        return "must_buy"
    if category == "toy_storage" and "child" in brief.residents:
        return "must_buy"
    if category in REUSE_FRIENDLY_CATEGORIES:
        return "reuse_or_buy"
    return "optional"


def _why_for(category: str, room_type: str, brief: DesignBrief) -> str:
    label = CATEGORY_LABELS.get(category, category)
    if category in STORAGE_CATEGORIES:
        return f"{label}对应收纳需求，适合先确认尺寸和开门方式。"
    if category == "toy_storage":
        return "亲子收纳能降低客厅杂物压力，也方便孩子自己取放。"
    if category == "sofa":
        return "沙发决定客厅坐感和主视觉，建议和电视柜/茶几一起确认尺度。"
    if category == "bed":
        return "床的尺寸会直接影响卧室通道和衣柜开门空间。"
    if room_type in {"kitchen", "bathroom"}:
        return "厨卫项和水电点位相关，建议尽早和设计师确认。"
    if brief.budget_cny and brief.budget_cny < 120000:
        return f"{label}可先用平价或旧家具过渡，把预算留给硬装与收纳。"
    return f"{label}用于完善当前布局，可按风格和预算逐步购买。"


def _keywords(category: str, room_type: str, brief: DesignBrief, material_hint: str | None) -> list[str]:
    label = CATEGORY_LABELS.get(category, category)
    style = brief.style.replace("_", " ")
    palette = [item for item in brief.color_palette[:2] if item]
    tokens = [label, room_type, style, *palette]
    if material_hint:
        tokens.append(material_hint)
    if category in STORAGE_CATEGORIES:
        tokens.append("定制收纳 尺寸可调")
    if "child" in brief.residents:
        tokens.append("圆角 安全")
    return list(dict.fromkeys(token for token in tokens if token))


def _shopping_items(
    option: LayoutOption,
    floorplan: FloorPlan,
    brief: DesignBrief,
) -> list[LivingShoppingItem]:
    room_types = _room_type_by_id(floorplan)
    items: list[LivingShoppingItem] = []
    for furniture in option.furniture_items:
        low, high = CATEGORY_ESTIMATES.get(furniture.category, (800, 5000))
        room_type = room_types.get(furniture.room_id, "unknown")
        items.append(
            LivingShoppingItem(
                category=furniture.category,
                label=CATEGORY_LABELS.get(furniture.category, furniture.category),
                room_id=furniture.room_id,
                room_type=room_type,
                priority=_priority_for(furniture.category, brief),
                dimensions_m=furniture.dimensions_m,
                estimated_price_cny_low=low,
                estimated_price_cny_high=high,
                search_keywords=_keywords(furniture.category, room_type, brief, furniture.material_hint),
                material_hint=furniture.material_hint,
                why=_why_for(furniture.category, room_type, brief),
            )
        )

    priority_order = {"must_buy": 0, "reuse_or_buy": 1, "optional": 2}
    return sorted(
        items,
        key=lambda item: (
            priority_order[item.priority],
            item.room_type,
            item.estimated_price_cny_low,
        ),
    )


def _phase_for_item(item: LivingShoppingItem) -> LivingBudgetPhaseKey:
    if item.category in ESSENTIAL_CATEGORIES or item.priority == "must_buy":
        return "move_in_essentials"
    if item.category in COMFORT_CATEGORIES:
        return "comfort_upgrade"
    if item.category in STYLE_CATEGORIES:
        return "style_finish"
    return "optional_later"


def _budget_phases(items: list[LivingShoppingItem], brief: DesignBrief) -> list[LivingBudgetPhase]:
    labels = {
        "move_in_essentials": "入住前必须确认",
        "comfort_upgrade": "住进去后 30-90 天升级",
        "style_finish": "风格收口",
        "optional_later": "可延后观察",
    }
    notes = {
        "move_in_essentials": ["优先确认大件尺寸、开门方向和插座/水电点位。"],
        "comfort_upgrade": ["先住一段时间再决定细节，避免一次买满。"],
        "style_finish": ["用软装和小件统一风格，不影响基础入住。"],
        "optional_later": ["预算紧时可先复用旧家具或空置观察。"],
    }
    grouped: dict[LivingBudgetPhaseKey, list[LivingShoppingItem]] = defaultdict(list)
    for item in items:
        grouped[_phase_for_item(item)].append(item)

    if brief.budget_cny:
        notes["move_in_essentials"].append(f"当前总预算约 {brief.budget_cny:,} 元，建议先保留 10%-15% 机动金。")

    phases: list[LivingBudgetPhase] = []
    for key in ("move_in_essentials", "comfort_upgrade", "style_finish", "optional_later"):
        phase_items = grouped.get(key, [])
        phases.append(
            LivingBudgetPhase(
                key=key,
                label=labels[key],
                estimated_budget_cny_min=int(sum(item.estimated_price_cny_low for item in phase_items)),
                estimated_budget_cny_max=int(sum(item.estimated_price_cny_high for item in phase_items)),
                included_categories=[item.label for item in phase_items],
                notes=notes[key],
            )
        )
    return phases


def _budget_fit(low: int, high: int, budget: int | None) -> LivingBudgetFit:
    if not budget:
        return "unknown"
    if high <= budget * 0.92:
        return "within_budget"
    if low <= budget:
        return "tight"
    return "over_budget"


def _discussion_cards(brief: DesignBrief, option: LayoutOption) -> list[LivingDiscussionCard]:
    cards = [
        LivingDiscussionCard(
            topic="预算优先级",
            prompt="哪些钱必须花在入住前，哪些可以住进去三个月后再买？",
            related_rooms=brief.room_priorities[:2],
            decision_hint="先锁定床、沙发、衣柜、厨卫项，再决定装饰件。",
        ),
        LivingDiscussionCard(
            topic="收纳边界",
            prompt="家里哪些物品一定要藏起来，哪些可以开放展示？",
            related_rooms=["living_room", "bedroom"],
            decision_hint="这会影响书柜、衣柜和电视柜是否做满墙。",
        ),
    ]
    if "child" in brief.residents or option.strategy == "family_friendly":
        cards.append(
            LivingDiscussionCard(
                topic="亲子活动区",
                prompt="客厅要保留多大可活动地面，玩具是否允许进入餐客厅？",
                related_rooms=["living_room"],
                decision_hint="确认后再决定茶几尺寸和儿童收纳位置。",
            )
        )
    if "work_from_home_desk" in brief.must_have:
        cards.append(
            LivingDiscussionCard(
                topic="办公位",
                prompt="办公位更需要安静、采光，还是能同时看顾孩子？",
                related_rooms=brief.room_priorities or ["living_room", "bedroom"],
                decision_hint="这会影响桌椅是否放在卧室、客厅或阳台附近。",
            )
        )
    return cards[:4]


def _designer_questions(floorplan: FloorPlan, brief: DesignBrief, option: LayoutOption) -> list[str]:
    questions = [
        "请确认所有门洞、窗户、梁位和管线点位是否与当前 FloorPlan 一致。",
        "请复核大件家具通道宽度，尤其是床边、衣柜前和客厅主通道。",
        "如果需要定制柜，请按当前方案确认每面墙是否可打孔、是否有插座或空调管线。",
    ]
    if floorplan.confidence < 0.75:
        questions.insert(0, "当前户型置信度偏低，请先用真实测量尺寸校正比例尺。")
    if "keep existing walls" in brief.constraints:
        questions.append("用户希望保留现有墙体，请标记任何不可拆或不建议改动的位置。")
    if option.hard_errors:
        questions.append("当前布局仍有硬错误，请先处理碰撞或挡门问题再进入深化。")
    return questions[:6]


def _recommended_next_step(package_items: list[LivingShoppingItem], option: LayoutOption, floorplan: FloorPlan) -> str:
    if option.hard_errors:
        return "先修正碰撞或挡门问题，再进入采购和渲染。"
    if floorplan.confidence < 0.75:
        return "先校正户型尺寸和门窗，再锁定大件清单。"
    must_buy_count = sum(1 for item in package_items if item.priority == "must_buy")
    return f"先确认 {must_buy_count} 个必须项的尺寸和预算，再把方案发给家人或设计师讨论。"


def build_living_plan_package(
    project_id: str,
    floorplan: FloorPlan,
    layout_options: list[LayoutOption],
    brief: DesignBrief,
    review: DesignReview | None = None,
) -> LivingPlanPackage:
    selected = _select_option(layout_options, review)
    shopping_items = _shopping_items(selected, floorplan, brief)
    phases = _budget_phases(shopping_items, brief)
    total_low = int(sum(item.estimated_price_cny_low for item in shopping_items))
    total_high = int(sum(item.estimated_price_cny_high for item in shopping_items))
    reuse_candidates = [
        f"{item.room_type} 的 {item.label} 可先复用或二手过渡"
        for item in shopping_items
        if item.priority == "reuse_or_buy"
    ][:5]
    caveats = [*floorplan.warnings[:3], *selected.hard_errors[:2], *selected.soft_warnings[:2]]
    if not caveats:
        caveats = ["这是概念阶段的生活方案包，施工和采购前仍需复核现场尺寸。"]

    if brief.budget_cny and total_high > brief.budget_cny:
        overshoot = ceil((total_high - brief.budget_cny) / 1000) * 1000
        caveats.append(f"按当前价格带上沿估算可能超出预算约 {overshoot:,} 元，可先延后软装小件。")

    return LivingPlanPackage(
        project_id=project_id,
        selected_option_id=selected.id,
        selected_strategy=selected.strategy,
        household_summary=_household_summary(brief, floorplan),
        recommended_next_step=_recommended_next_step(shopping_items, selected, floorplan),
        budget_total_low_cny=total_low,
        budget_total_high_cny=total_high,
        budget_fit=_budget_fit(total_low, total_high, brief.budget_cny),
        budget_phases=phases,
        shopping_items=shopping_items,
        reuse_candidates=reuse_candidates,
        family_discussion_cards=_discussion_cards(brief, selected),
        designer_handoff_questions=_designer_questions(floorplan, brief, selected),
        caveats=caveats[:7],
    )
