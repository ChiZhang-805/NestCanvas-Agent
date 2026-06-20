from __future__ import annotations

from app.schemas.domain import (
    DesignBrief,
    DesignReview,
    FloorPlan,
    HomeCoachPackage,
    HomeCoachRoomCard,
    LayoutOption,
    LivingPlanPackage,
    PortableServiceSpec,
    ProjectWorkflow,
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


def _select_option(options: list[LayoutOption], review: DesignReview | None) -> LayoutOption | None:
    if not options:
        return None
    if review and review.best_option_id:
        for option in options:
            if option.id == review.best_option_id:
                return option
    return max(options, key=lambda option: option.score)


def _room_notes(room_type: str, brief: DesignBrief, furniture_labels: list[str]) -> list[str]:
    notes: list[str] = []
    if "living" in room_type:
        notes.append("优先保留连续活动地面，避免茶几和儿童收纳把主通道切碎。")
    if "bedroom" in room_type:
        notes.append("先确认床边通道、衣柜开门和插座位置，再决定床头柜和矮柜。")
    if "kitchen" in room_type or "dining" in room_type:
        notes.append("餐厨项和水电/动线相关，建议在软装采购前先锁定尺寸。")
    if "bathroom" in room_type:
        notes.append("卫浴项必须复核下水、门扇和干湿区边界。")
    if brief.storage_level == "high" and any(label in furniture_labels for label in ["衣柜", "书柜", "儿童收纳", "电视柜"]):
        notes.append("这是高收纳关键空间，建议用真实物品清单反推柜体分区。")
    return notes[:4] or ["这个空间已具备基础家具占位，下一步适合用真实尺寸做微调。"]


def _room_risks(room_type: str, floorplan_confidence: float, option: LayoutOption | None) -> list[str]:
    risks: list[str] = []
    if floorplan_confidence < 0.75:
        risks.append("户型置信度偏低，任何大件采购前都要重新量尺。")
    if option and option.hard_errors:
        risks.append("当前方案仍有硬错误，先处理碰撞或挡门再采购。")
    if option and option.soft_warnings:
        risks.append("存在通道/贴边类软风险，建议现场复核净宽。")
    if "bathroom" in room_type or "kitchen" in room_type:
        risks.append("厨卫涉及管线，不能仅凭概念布局下单。")
    return risks[:4]


def _shopping_focus(living_plan: LivingPlanPackage, room_id: str) -> list[str]:
    return [
        f"{item.label}：{item.priority}，预算约 {item.estimated_price_cny_low:,}-{item.estimated_price_cny_high:,} 元"
        for item in living_plan.shopping_items
        if item.room_id == room_id
    ][:5]


def _measurement_tasks(room_type: str, furniture_labels: list[str]) -> list[str]:
    tasks = ["复核房间净尺寸、门洞宽度、窗台高度和插座位置。"]
    if "床" in furniture_labels:
        tasks.append("量床两侧和床尾净通道，确认床垫尺寸不会压缩衣柜开门。")
    if "衣柜" in furniture_labels or "书柜" in furniture_labels:
        tasks.append("量柜体所在墙面长度、梁位、踢脚线和开门/抽屉前方空间。")
    if "沙发" in furniture_labels:
        tasks.append("量沙发到电视墙、阳台门和入户动线的距离。")
    if "bathroom" in room_type or "kitchen" in room_type:
        tasks.append("拍摄水电点位、地漏、烟道和门套照片，交给设计师复核。")
    return tasks[:5]


def _visual_prompt(room_type: str, brief: DesignBrief, furniture_labels: list[str]) -> str:
    palette = ", ".join(brief.color_palette[:3]) or "warm neutral palette"
    furniture = ", ".join(furniture_labels[:5]) or "basic furniture"
    return (
        f"Residential {room_type}, style {brief.style}, palette {palette}, "
        f"show realistic scale for {furniture}, soft daylight, tidy lived-in home, no demolition promise."
    )


def _portable_services(workflow: ProjectWorkflow) -> list[PortableServiceSpec]:
    return [
        *workflow.portable_services,
        PortableServiceSpec(
            key="family_share_markdown",
            label="家庭讨论 Markdown",
            service_type="export",
            purpose="把家庭讨论卡、每房间量尺任务和采购重点输出为可复制的 Markdown。",
            inputs=["HomeCoachPackage"],
            outputs=["home_coach.md"],
            status="ready",
        ),
        PortableServiceSpec(
            key="designer_handoff_json",
            label="设计师交接 JSON",
            service_type="export",
            purpose="把 FloorPlan、最佳方案、风险、量尺任务和待确认问题打包给外部设计师。",
            inputs=["HomeCoachPackage", "FloorPlan", "LayoutOption"],
            outputs=["designer_handoff.json"],
            status="ready",
        ),
    ]


def build_home_coach_package(
    project_id: str,
    workflow: ProjectWorkflow,
    floorplan: FloorPlan,
    brief: DesignBrief,
    layout_options: list[LayoutOption],
    living_plan: LivingPlanPackage,
    review: DesignReview | None = None,
) -> HomeCoachPackage:
    selected = _select_option(layout_options, review)
    items_by_room: dict[str, list[str]] = {}
    if selected:
        for item in selected.furniture_items:
            items_by_room.setdefault(item.room_id, []).append(CATEGORY_LABELS.get(item.category, item.category))

    room_cards: list[HomeCoachRoomCard] = []
    for room in floorplan.rooms:
        furniture_labels = items_by_room.get(room.id, [])
        headline = f"{room.room_type}：{len(furniture_labels)} 个家具占位，面积约 {room.area_m2:.1f} m2"
        room_cards.append(
            HomeCoachRoomCard(
                room_id=room.id,
                room_type=room.room_type,
                headline=headline,
                current_furniture=furniture_labels,
                daily_use_notes=_room_notes(room.room_type, brief, furniture_labels),
                risks=_room_risks(room.room_type, floorplan.confidence, selected),
                shopping_focus=_shopping_focus(living_plan, room.id),
                measurement_tasks=_measurement_tasks(room.room_type, furniture_labels),
                visual_prompt=_visual_prompt(room.room_type, brief, furniture_labels),
            )
        )

    family_script = [
        f"{card.topic}：{card.prompt} 建议：{card.decision_hint}"
        for card in living_plan.family_discussion_cards
    ]
    designer_packet = [
        *living_plan.designer_handoff_questions,
        "请把 HomeCoachRoomCard 的量尺任务逐项关闭后再进入最终采购清单。",
    ]
    llm_upgrade_plan = [
        *workflow.llm_modules,
        PortableServiceSpec(
            key="room_scene_reasoner",
            label="逐房间场景推理",
            service_type="api",
            purpose="用推理模型按一天的生活动线检查每个房间是否满足家庭成员的真实行为。",
            inputs=["HomeCoachRoomCard[]", "DesignBrief"],
            outputs=["scenario_conflicts", "room_priority_changes"],
            status="ready" if selected else "blocked",
        ),
    ]
    return HomeCoachPackage(
        project_id=project_id,
        summary=(
            f"已把 {len(room_cards)} 个空间、{len(living_plan.shopping_items)} 个采购项和 "
            f"{len(family_script)} 张家庭讨论卡整合成可交付 Home Coach 包。"
        ),
        workflow=workflow,
        selected_option_id=selected.id if selected else None,
        room_cards=room_cards,
        family_script=family_script,
        designer_packet=designer_packet[:8],
        llm_upgrade_plan=llm_upgrade_plan,
        portable_services=_portable_services(workflow),
        caveats=[
            "Home Coach 是沟通和行动包，不替代施工图、结构判断或现场复尺。",
            "所有视觉提示词只用于概念表达，不承诺实际施工效果。",
            *living_plan.caveats[:4],
        ],
    )
