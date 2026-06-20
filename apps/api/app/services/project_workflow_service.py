from __future__ import annotations

from typing import Literal

from app.schemas.domain import Asset, PortableServiceSpec, ProjectDetail, ProjectWorkflow, WorkflowStep


StepStatus = Literal["done", "current", "available", "blocked"]


def _step(
    key: str,
    label: str,
    status: StepStatus,
    artifact_count: int,
    blockers: list[str],
    next_actions: list[str],
    automation_hint: str,
) -> WorkflowStep:
    return WorkflowStep(
        key=key,
        label=label,
        status=status,
        artifact_count=artifact_count,
        blockers=blockers,
        next_actions=next_actions,
        automation_hint=automation_hint,
    )


def _import_assets(assets: list[Asset]) -> list[Asset]:
    return [asset for asset in assets if asset.asset_type in {"image", "pdf"}]


def _first_not_done(steps: list[WorkflowStep]) -> str:
    for step in steps:
        if step.status in {"current", "available", "blocked"}:
            return step.key
    return steps[-1].key if steps else "done"


def _service_specs(detail: ProjectDetail) -> tuple[list[PortableServiceSpec], list[PortableServiceSpec]]:
    has_asset = bool(_import_assets(detail.assets))
    has_floorplan = bool(detail.floorplans)
    has_brief = bool(detail.briefs)
    has_options = bool(detail.layout_options)
    has_renders = bool(detail.renders)

    llm_modules = [
        PortableServiceSpec(
            key="vision_floorplan_triage",
            label="视觉户型体检",
            service_type="api",
            purpose="用多模态模型读取上传图、售楼册或 PDF 页面，提取比例尺、房间标签、门窗和低置信区域。",
            inputs=["asset.local_path", "prepared_image.local_path"],
            outputs=["vision_notes", "parse_warnings", "measurement_tasks"],
            status="ready" if has_asset else "blocked",
        ),
        PortableServiceSpec(
            key="reasoning_layout_tradeoff",
            label="方案取舍推理",
            service_type="api",
            purpose="在本地几何评分基础上，用推理模型解释家庭成员、预算、收纳、通道之间的取舍。",
            inputs=["FloorPlan", "DesignBrief", "LayoutOption[]", "DesignReview"],
            outputs=["family_script", "designer_packet", "room_cards"],
            status="ready" if has_floorplan and has_brief and has_options else "blocked",
        ),
        PortableServiceSpec(
            key="text_shopping_copywriter",
            label="采购文案生成",
            service_type="api",
            purpose="把生活清单转成用户能复制给家人、设计师或导购的短文案。",
            inputs=["LivingPlanPackage"],
            outputs=["shopping_messages", "handoff_questions"],
            status="ready" if has_options else "blocked",
        ),
    ]
    portable_services = [
        PortableServiceSpec(
            key="home_coach_pack",
            label="Home Coach JSON",
            service_type="export",
            purpose="生成可分享的家庭教练包，供移动端、小程序或设计师工作台直接消费。",
            inputs=["ProjectDetail", "LivingPlanPackage"],
            outputs=["HomeCoachPackage"],
            status="ready" if has_floorplan and has_brief and has_options else "blocked",
        ),
        PortableServiceSpec(
            key="measurement_task_worker",
            label="量尺任务 Worker",
            service_type="worker",
            purpose="把低置信户型、未标注门窗和大件家具转成可逐项勾选的现场量尺任务。",
            inputs=["FloorPlan.confidence", "Room[]", "FurnitureItem[]"],
            outputs=["measurement_tasks"],
            status="ready" if has_floorplan else "blocked",
        ),
        PortableServiceSpec(
            key="render_prompt_cli",
            label="渲染提示词 CLI",
            service_type="cli",
            purpose="在无网页环境下批量为布局方案生成风格提示词，便于接入图片生成队列。",
            inputs=["LayoutOption", "DesignBrief"],
            outputs=["render_prompt.txt"],
            status="ready" if has_options and has_brief and not has_renders else "planned",
        ),
    ]
    return llm_modules, portable_services


def build_project_workflow(detail: ProjectDetail) -> ProjectWorkflow:
    import_assets = _import_assets(detail.assets)
    prepared_assets = [asset for asset in detail.assets if asset.asset_type == "prepared_image"]
    has_asset = bool(import_assets)
    has_floorplan = bool(detail.floorplans)
    has_brief = bool(detail.briefs)
    has_options = bool(detail.layout_options)
    has_living_inputs = has_floorplan and has_brief and has_options
    has_renders = bool(detail.renders)

    steps = [
        _step(
            "upload",
            "上传素材",
            "done" if has_asset or has_floorplan else "current",
            len(import_assets) or (1 if has_floorplan else 0),
            [],
            ["上传户型图、售楼册 PDF、截图或手机拍摄照片。"] if not has_asset and not has_floorplan else ["素材或户型模板已就绪，可进行输入整理。"],
            "接收图片/PDF，保存为 Asset，并记录原始文件名、尺寸和 MIME。",
        ),
        _step(
            "prepare_input",
            "整理输入",
            "done" if prepared_assets or (has_floorplan and not has_asset) else "available" if has_asset else "blocked",
            len(prepared_assets) or (1 if has_floorplan and not has_asset else 0),
            [] if has_asset or has_floorplan else ["需要先上传图片/PDF，或使用草稿底图/户型库模板。"],
            ["运行 OpenCV 透视拉正、裁剪、增强和视觉提示。"] if has_asset else ["已使用结构化户型，可在户型页继续校正。"],
            "将嘈杂照片变成 parser 优先使用的 prepared_image，并附带质量分和建议。",
        ),
        _step(
            "floorplan",
            "校正户型",
            "done" if has_floorplan else "available" if has_asset else "blocked",
            len(detail.floorplans),
            [] if has_asset else ["缺少可解析素材，也可以先使用草稿底图或户型库模板。"],
            ["解析或选择户型库模板，再人工校正比例尺、房间类型和门窗。"],
            "产出可验证 FloorPlan JSON，所有后续几何判断都只信任这个结构。",
        ),
        _step(
            "brief",
            "结构化需求",
            "done" if has_brief else "available",
            len(detail.briefs),
            [],
            ["填写家庭成员、预算、风格、收纳、禁忌和必须项。"],
            "文本模型抽取 DesignBrief；无 Key 时走 deterministic local parser。",
        ),
        _step(
            "layout_options",
            "生成方案",
            "done" if has_options else "available" if has_floorplan and has_brief else "blocked",
            len(detail.layout_options),
            [] if has_floorplan and has_brief else ["需要 FloorPlan 和 DesignBrief。"],
            ["生成三套布局，评估碰撞、挡门、通道和生活方式适配。"],
            "本地几何引擎给出家具坐标，LLM 只做解释和沟通增强。",
        ),
        _step(
            "living_plan",
            "生活清单",
            "available" if has_living_inputs else "blocked",
            1 if has_living_inputs else 0,
            [] if has_living_inputs else ["需要布局方案。"],
            ["生成预算分期、采购优先级、家庭讨论卡和设计师交接问题。"],
            "把布局从图形方案转成普通家庭能执行的清单。",
        ),
        _step(
            "home_coach",
            "家庭教练包",
            "available" if has_living_inputs else "blocked",
            1 if has_living_inputs else 0,
            [] if has_living_inputs else ["需要 FloorPlan、DesignBrief 和 LayoutOption。"],
            ["生成每个房间的使用建议、量尺任务、视觉提示和便携式服务清单。"],
            "整合 workflow、living plan、room cards 和 LLM/worker 扩展点。",
        ),
        _step(
            "render_export",
            "渲染与导出",
            "done" if has_renders else "available" if has_options else "blocked",
            len(detail.renders),
            [] if has_options else ["需要先生成布局方案。"],
            ["生成概念图并导出包含 Home Coach 的项目 JSON。"],
            "图片生成只产出概念表达，导出文件保留所有结构化中间件。",
        ),
    ]
    done_count = sum(1 for step in steps if step.status == "done")
    available_count = sum(1 for step in steps if step.status == "available")
    blocked_count = sum(1 for step in steps if step.status == "blocked")
    readiness = int(round((done_count * 100 + available_count * 60) / max(len(steps), 1)))
    if blocked_count:
        summary = f"当前有 {blocked_count} 个环节被前置资料阻断，建议先处理 { _first_not_done(steps) }。"
    elif has_living_inputs:
        summary = "项目已具备完整家庭设计闭环，可以生成 Home Coach、渲染和导出。"
    else:
        summary = "项目正在推进中，下一步按当前工作流补齐结构化资料。"

    llm_modules, portable_services = _service_specs(detail)
    return ProjectWorkflow(
        project_id=detail.id,
        current_step=_first_not_done(steps),
        readiness_score=max(0, min(100, readiness)),
        summary=summary,
        steps=steps,
        automation_plan=[
            "route 层只负责编排数据读写；解析、布局、评审、生活清单、教练包分别由 service 层独立实现。",
            "所有几何坐标由本地引擎生成和校验；多模态/推理/文本模型只负责理解、解释和可读交付。",
            "每个 LLM 模块都必须有 deterministic fallback，确保测试、本地 demo 和无 Key 环境稳定。",
        ],
        llm_modules=llm_modules,
        portable_services=portable_services,
    )
