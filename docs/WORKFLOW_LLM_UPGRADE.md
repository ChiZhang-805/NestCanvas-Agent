# NestCanvas Workflow and LLM Upgrade Plan

本文档记录本轮已经落地的 NestCanvas 后端工作流升级，以及后续接入大模型、视觉能力和检索数据库时的具体实现路线。产品定位保持为 ToC：帮助普通家庭把户型、预算、审美和生活方式转成可讨论、可采购、可交接的家居行动包。

## 1. 产品边界

NestCanvas 不做地产投拓、不做报批强排、不输出施工图结论。它的核心用户是买房、租房、装修和软装决策中的家庭用户。

核心交付物：

- 可校正 `FloorPlan JSON`：让用户和设计师对同一个户型结构说话。
- 多套 `LayoutOption`：本地几何生成家具占位、通道和碰撞评分。
- `LivingPlanPackage`：把方案转成预算分期、采购优先级、家庭讨论卡。
- `HomeCoachPackage`：本轮新增的家庭教练包，面向移动端、小程序、设计师工作台或离线导出。

大模型的边界：

- 视觉模型用于读取户型图、售楼册、低置信区域和量尺提示。
- 推理模型用于解释取舍、按家庭成员行为检查空间冲突。
- 文本模型用于把结构化清单改写成用户能复制给家人、设计师、导购的表达。
- 家具坐标、碰撞、门窗遮挡、通道净宽仍由本地代码计算。

## 2. 已落地的后端工作流拆分

新增 service：

- `apps/api/app/services/project_workflow_service.py`
  - 输入：`ProjectDetail`
  - 输出：`ProjectWorkflow`
  - 职责：把上传、输入整理、户型校正、需求结构化、方案生成、生活清单、家庭教练包、渲染导出拆成可显示、可阻断、可自动化的步骤。
- `apps/api/app/services/home_coach_service.py`
  - 输入：`ProjectWorkflow`、`FloorPlan`、`DesignBrief`、`LayoutOption[]`、`LivingPlanPackage`、可选 `DesignReview`
  - 输出：`HomeCoachPackage`
  - 职责：生成逐房间卡片、采购重点、现场量尺任务、家庭沟通脚本、设计师交接包、LLM 升级计划和便携服务列表。

新增 schema：

- `WorkflowStep`
- `PortableServiceSpec`
- `ProjectWorkflow`
- `HomeCoachRoomCard`
- `HomeCoachPackage`

新增 API：

- `GET /api/projects/{project_id}/workflow`
- `POST /api/projects/{project_id}/home-coach`

导出升级：

- `POST /api/projects/{project_id}/export` 现在在资料齐全时会附带：
  - `workflow`
  - `design_review`
  - `living_plan`
  - `home_coach`

## 3. 前端功能落地

新增页面：

- `apps/web/app/projects/[id]/coach/page.tsx`

页面能力：

- 展示工作流 readiness、当前步骤、阻断项和下一步动作。
- 展示每个房间的家庭教练卡，包括日常使用建议、风险、采购重点、量尺任务和视觉提示词。
- 展示可接入的大模型模块和便携式服务。

导航升级：

- `apps/web/components/StepNav.tsx` 新增“助手”步骤，使 C 端流程从“清单”自然延展到“家庭教练包”。

前端 API/type：

- `getProjectWorkflow(projectId)`
- `createHomeCoach(projectId)`
- zod schema 覆盖 `ProjectWorkflow` 和 `HomeCoachPackage`，避免前后端结构漂移。

## 4. LLM / Vision / Text 模块设计

### 4.1 vision_floorplan_triage

定位：视觉户型体检。

输入：

- 原始图片、PDF 页面截图、`prepared_image`
- OpenCV 的质量分、裁剪框、透视校正结果

输出：

- 低置信区域
- 房间标签候选
- 门窗/承重/比例尺疑问
- 量尺任务初稿

落地方式：

- 现在以 `PortableServiceSpec` 暴露为 ready/blocked 状态。
- 后续接入点放在 `openai_service.analyze_floorplan_image()` 与 `input_preparation_service.py`。
- 视觉输出不得直接覆盖 `FloorPlan`，必须进入“建议/待确认”字段，由用户或 deterministic parser 合并。

### 4.2 reasoning_layout_tradeoff

定位：方案取舍推理。

输入：

- `FloorPlan`
- `DesignBrief`
- `LayoutOption[]`
- `DesignReview`

输出：

- 家庭成员视角的取舍解释
- 房间优先级调整建议
- 风险转行动建议

落地方式：

- 现在由 `HomeCoachPackage.family_script`、`room_cards`、`designer_packet` 先用本地规则生成。
- 后续可在 `home_coach_service.py` 中增加 `openai_service.reason_home_layout()`，失败时保持当前本地输出。

### 4.3 text_shopping_copywriter

定位：采购/交接文案生成。

输入：

- `LivingPlanPackage`
- `HomeCoachRoomCard[]`

输出：

- 家庭群讨论版本
- 给设计师的交接版本
- 给导购/家具店的尺寸和风格询问版本

落地方式：

- 当前由 `family_script` 和 `designer_packet` 输出结构化文本。
- 后续文本模型只负责改写，不改变价格、尺寸和优先级字段。

### 4.4 room_scene_reasoner

定位：逐房间生活场景推理。

输入：

- `HomeCoachRoomCard[]`
- `DesignBrief`
- 家庭成员和一天行为动线

输出：

- 早晚高峰使用冲突
- 孩子/老人/宠物的安全风险
- 需要先买、可复用、可延后采购的解释

落地方式：

- 本轮已加入 `HomeCoachPackage.llm_upgrade_plan`。
- 后续实现时建议先做纯文本 JSON 输出，字段为 `scenario_conflicts` 和 `room_priority_changes`。

## 5. 便携式服务设计

已落地为 `PortableServiceSpec`：

- `home_coach_pack`
  - 输出完整 `HomeCoachPackage`
  - 适合小程序、移动端、设计师后台直接消费
- `measurement_task_worker`
  - 将低置信户型和大件家具转成现场量尺任务
  - 未来可做成后台任务或手机端 checklist
- `render_prompt_cli`
  - 批量生成渲染提示词
  - 适合接入图片生成队列
- `family_share_markdown`
  - 从 `HomeCoachPackage` 导出 Markdown
  - 适合家庭群、飞书/Notion、微信收藏
- `designer_handoff_json`
  - 给外部设计师的结构化交接 JSON
  - 应包含户型、最佳方案、风险、量尺任务和待确认问题

下一步建议新增具体导出 endpoint：

- `POST /api/projects/{project_id}/home-coach/export?format=markdown`
- `POST /api/projects/{project_id}/home-coach/export?format=designer_json`

## 6. 数据库接入路线

### 6.1 户型检索库

优先目标：

- `FloorPlan` JSON 索引
- 面积、卧室数、卫生间数、房间邻接、开间/进深、采光面、动线标签
- source/license/effective_date 字段必须保留

候选数据：

- Swiss Dwellings：更适合许可清晰的指标检索参考。
- RPLAN：适合研究大规模户型关系，商用前必须复核许可。
- CubiCasa5K：适合训练/评估解析模型，CC BY-NC 4.0 不适合作为商业模板直接售卖。

索引建议：

- SQLite/FastAPI 本地 demo：`floorplan_templates.parquet + sqlite fts`
- 生产：PostgreSQL JSONB + pgvector，或专门的向量库保存 room graph embedding。

### 6.2 家具尺寸库

字段：

- `category`
- `width_m`
- `depth_m`
- `height_m`
- `clearance_m`
- `style_tags`
- `material`
- `price_band`
- `source_license`

使用位置：

- `layout_generator` 选择更真实的尺寸。
- `living_plan_service` 给出预算分期。
- `home_coach_service` 生成量尺任务和导购询问文案。

数据来源：

- 自建标准件库。
- 品牌授权商品 feed。
- 设计师/软装团队维护的公司知识库。

不要直接抓取未授权电商数据作为生产库。

### 6.3 材料/软装价格库

字段：

- `material_type`
- `brand_level`
- `city`
- `unit_price_low/high`
- `maintenance_note`
- `style_tags`
- `lead_time`

使用位置：

- `LivingPlanPackage.budget_phases`
- `shopping_focus`
- 风格提示词和设计师交接包

### 6.4 3D/风格研究库

候选：

- 3D-FRONT / 3D-FUTURE 可用于研究家具关系和风格搭配。

限制：

- 严格按研究/非商业许可处理。
- 不应把素材直接打包给商业用户。

## 7. 验收标准

后端：

- `GET /api/projects/{project_id}/workflow` 在无资产、半完成、完整项目都能给出合理状态。
- `POST /api/projects/{project_id}/home-coach` 在缺少户型/需求/方案时返回明确 400；完整项目返回房间卡和便携服务。
- `POST /api/projects/{project_id}/export` 在完整项目中包含 `workflow`、`living_plan`、`home_coach`。

前端：

- `/projects/[id]/coach` 不因缺少 Home Coach 而空白。
- 工作流、房间卡、LLM 模块、便携服务都能在移动端和桌面端阅读。

测试：

- `apps/api/tests/test_api_happy_path.py` 覆盖 workflow/home-coach/export。
- `apps/api/tests/test_schemas_and_services.py` 覆盖纯 service 输出。
- `apps/web` typecheck 覆盖新类型和页面。

## 8. 下一轮最值得做的代码任务

1. 增加 `home_coach/export` endpoint，输出 Markdown 和 designer JSON。
2. 在 `openai_service.py` 增加 `reason_home_layout()`，只生成解释和沟通文本，不改坐标。
3. 将家具尺寸库从 hardcoded rule 拆成 `data/furniture_dimensions.seed.json`，并加入检索 service。
4. 给 `/coach` 页增加 Markdown 下载按钮和设计师交接 JSON 下载按钮。
5. 把 `measurement_task_worker` 做成可逐项完成的 checklist，并写入项目资产或独立表。
