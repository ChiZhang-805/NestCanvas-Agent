from app.schemas.domain import DesignBrief, FloorPlan, LayoutOption


def summarize_layout_for_prompt(
    floorplan: FloorPlan, layout_option: LayoutOption, design_brief: DesignBrief
) -> str:
    room_count = len(floorplan.rooms)
    item_count = len(layout_option.furniture_items)
    return (
        f"{room_count} rooms, {item_count} furniture placeholders, "
        f"strategy {layout_option.strategy}, style {design_brief.style}"
    )
