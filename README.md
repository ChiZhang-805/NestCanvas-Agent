# NestCanvas Agent（栖画）

NestCanvas Agent 是面向买房、租房、装修用户的 C 端 AI 家居设计画布。MVP 把户型图/草图/房间图上传为资产，解析成可校正的 `FloorPlan JSON`，再从自然语言需求抽取 `DesignBrief`，由本地几何与规则引擎生成多套家具布局，最后生成带免责声明的概念效果图。

核心边界：OpenAI 只负责语义理解、视觉提示、渲染 prompt 和概念图生成；家具坐标、碰撞、门口遮挡、通道校验都由本地代码完成。

## 技术栈

- 后端：FastAPI、Pydantic v2、SQLAlchemy 2、Alembic、PostgreSQL 16、Redis/RQ、Pillow、OpenCV headless、Shapely、OpenAI Python SDK。
- 前端：Next.js App Router、TypeScript、Tailwind、Zustand、zod、SVG。
- 基础设施：`infra/docker-compose.yml` 启动 `postgres:16` 和 `redis:7`。

## WSL2 Ubuntu 22.04 启动

```bash
cd /home/chi/Project/NestCanvas-Agent
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d
```

后端：

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd apps/web
npm install
npm run dev
```

默认前端通过 Next.js 同源 `/api` 和 `/storage` 代理访问后端，代理目标为：

```env
NESTCANVAS_API_BASE_URL=http://127.0.0.1:8000
```

`NEXT_PUBLIC_API_BASE_URL` 只在需要浏览器直连后端时设置；默认留空可避免跨端口 CORS 和本机端口冲突。

打开 `http://localhost:3000`。

## Render Blueprint 部署

本仓库根目录包含 `render.yaml`，可用 Render Blueprint 一键创建两个 public web services：

- `nestcanvas-api`：FastAPI 后端，健康检查 `/healthz`。
- `nestcanvas-web`：Next.js 前端，面向用户公开访问；前端通过 `NESTCANVAS_API_BASE_URL` 代理 `/api/*` 和 `/storage/*` 到后端。Render Free plan 下默认使用 API 的 public `.onrender.com` 地址，避免 free web service 不能接收私网流量的问题。

一键部署链接：

```text
https://render.com/deploy?repo=https://github.com/ChiZhang-805/NestCanvas-Agent
```

部署完成后，把 `nestcanvas-web` 的 `https://...onrender.com` 地址分享给用户即可。默认无 Key 时会走 deterministic mock；用户可以直接在网页里的 **OpenAI API Key** 面板填写自己的 Key，并切换解释模型、快速模型和图片模型。Key 和模型选择只保存在当前浏览器 localStorage，并通过 `X-OpenAI-API-Key`、`X-OpenAI-Model-Text`、`X-OpenAI-Model-Fast`、`X-OpenAI-Model-Image` 请求头临时发送给 API。Render Dashboard 里的 `OPENAI_API_KEY` 只是可选的站主预置方式，不是必需。

注意：当前 Blueprint 使用 Render free plan 和本地 SQLite/文件存储，适合公开 demo。免费服务可能休眠，且重启/重新部署后上传文件和 SQLite 状态不保证长期保留；生产版应改接 Render Postgres/对象存储或外部数据库。

## 环境变量

`.env.example` 包含：

- `DATABASE_URL`：默认示例指向本地 Docker PostgreSQL。
- `REDIS_URL`：RQ worker 使用的 Redis 地址。
- `STORAGE_DIR`：上传资产、mock render 的本地存储目录。
- `SYNC_JOBS`：`true` 时解析任务同步执行，适合本地 demo 和测试；生产可设为 `false` 并启动 RQ worker。
- `OPENAI_API_KEY`：为空时所有 AI 相关函数走 deterministic mock。
- `OPENAI_MODEL_TEXT`、`OPENAI_MODEL_FAST`、`OPENAI_IMAGE_MODEL`：集中由 `openai_service.py` 读取；网页端可按当前浏览器覆盖这些模型。
- `NESTCANVAS_API_BASE_URL`：Next.js `/api` 和 `/storage` 代理目标，默认 `http://127.0.0.1:8000`。
- `NEXT_PUBLIC_API_BASE_URL`：可选浏览器直连 API 地址，默认留空。

也可以不写 `.env` 的 `OPENAI_API_KEY`，直接在网页里的 **OpenAI API Key** 面板填写。网页 Key 和模型选择只保存在当前浏览器 `localStorage`，随后通过请求头发送给本机 FastAPI；后端不会把它写入数据库。适合本地演示、公开 demo 或临时切换账号；长期部署可把站主默认 Key 放到 `.env`。

## 测试

后端：

```bash
python -m pytest apps/api/tests -q
```

前端类型检查：

```bash
cd apps/web
npm run typecheck
```

当前验证结果：

- `pytest apps/api/tests -q`：18 passed。
- `npm run typecheck`：通过。
- `npm run lint`：无警告或错误。
- `npm run build`：通过。

详细升级设计见 [docs/WORKFLOW_LLM_UPGRADE.md](docs/WORKFLOW_LLM_UPGRADE.md)，包含后端工作流拆分、Home Coach、LLM/视觉/文本模块、便携服务和未来数据库接入路线。检索库数据导入说明见 [docs/DATA_LIBRARY_IMPORT.md](docs/DATA_LIBRARY_IMPORT.md)。

## 已实现功能

- 项目创建、聚合读取。
- 网页 OpenAI 设置面板；支持浏览器 Key/模型覆盖、`.env` Key、无 Key mock 三种模式。
- PNG/JPG/WEBP/PDF 上传到 `storage/` 并写入 DB。
- 输入整理：支持手机拍摄售楼册、截图、偏斜/低对比图片，先用 OpenCV 做透视拉正、内容裁剪、对比度增强和线条锐化，再生成 `prepared_image` 供解析优先使用。
- 无图兜底：用户暂时没有空房照或户型图时，可先创建低置信度草稿底图进入需求和方案流程，后续再用真实素材替换校正。
- 户型库检索：内置结构化种子模板，支持按关键词、卧室数、面积和数据源筛选；选中模板后可直接写入当前项目的 `FloorPlan`。
- `parse-floorplan` job 状态记录；MVP parser 使用图片检查 + fallback fixture 生成 `FloorPlan`。
- `FloorPlan` PATCH 校正保存。
- `DesignBrief` 抽取：有 Key 时优先 OpenAI Responses API structured parse，失败或无 Key 时 deterministic mock。
- 本地 Shapely 几何函数：polygon normalize/area、bbox polygon、碰撞、挡门、clearance、layout score。
- 三套布局策略：`balanced_storage`、`open_living`、`family_friendly`。
- 设计评审：本地规则计算收纳、动线、生活方式适配和风险控制分；有 OpenAI Key 时可生成更像设计顾问的中文方案诊断。
- 生活方案包：把最佳布局转成普通用户可执行的预算分期、采购优先级、可复用家具、家庭讨论卡和设计师交接问题，接口为 `POST /api/projects/{project_id}/living-plan`，前端页面为 `/projects/[id]/living`。
- 项目工作流：`GET /api/projects/{project_id}/workflow` 将上传、输入整理、户型校正、需求结构化、布局、生活清单、家庭教练包、渲染导出拆成可显示的步骤，并返回 LLM 模块和便携服务状态。
- Home Coach 家庭教练包：`POST /api/projects/{project_id}/home-coach` 生成逐房间建议、采购重点、量尺任务、家庭沟通脚本、设计师交接包和后续 LLM 升级计划；前端页面为 `/projects/[id]/coach`。
- 概念渲染：有 Key 时优先 `OPENAI_IMAGE_MODEL`，失败或无 Key 时 mock SVG；所有 render 带免责声明和 prompt。
- 项目 JSON 导出，包含 FloorPlan、DesignBrief、布局方案、项目工作流、生活方案包、Home Coach、渲染资产和本地设计评审，作为和家人、设计师或销售沟通的结构化交付件。
- Next.js 七步页面：上传、户型、需求、方案、清单、助手、渲染。

## 户型数据集接入策略

当前产品内置的是 NestCanvas synthetic seed templates，没有复制外部数据。适合先验证用户检索流程、筛选字段和模板写入能力。本项目不是商业模板库，外部数据的 license 字段主要用于来源追溯、归属和样本治理。后续可接入的数据源：

- RPLAN：适合做大规模住宅户型检索、面积/房间数/邻接关系统计；作为研究候选源时保留原始来源和版本信息。
- CubiCasa5K：5k 户型图和语义标注，适合训练/评估户型解析模型；官方 Zenodo 页面标注为 CC BY-NC-SA 4.0。
- Swiss Dwellings：Zenodo 页面为 CC BY 4.0，适合参考更丰富的住宅指标检索方式，例如几何、采光、噪声、可达性等。

推荐数据处理流水线：下载原始数据 -> 转换为统一 `FloorPlan` JSON -> 提取 `area_m2 / bedrooms / bathrooms / room_types / tags / source_license` -> 生成 preview -> 进入 `/api/floorplan-library` 检索索引。

为了让 C 端用户真正能检索和行动，后续建议拆成四类库：

- 户型检索库：优先接 Swiss Dwellings、CubiCasa5K、RPLAN 这类公开/研究数据做指标检索和解析验证；正式导入时保留 source、version、license、attribution 字段。
- 家具尺寸库：从品牌合作、公开授权商品 feed 或自建标准件库收集 `category / width / depth / height / price_band / material / style_tags`，不要直接抓取无授权电商数据。
- 软装与材料库：维护地板、墙漆、柜体板材、布艺、灯具的价格带和风格标签，用于生活方案包的预算分期和关键词。
- 3D/布局研究库：3D-FRONT、3D-FUTURE 等适合研究家具关系和风格搭配；进入产品检索库时保留来源和版本元数据。

## 限制与后续替换点

- 户型解析当前是 MVP fallback，`apps/api/app/services/floorplan_parser.py` 可替换为更强的 segmentation/vectorization pipeline；输入清理在 `apps/api/app/services/input_preparation_service.py`，适合继续接入更强的版面检测、OCR 和图像分割。
- `SYNC_JOBS=true` 默认同步执行，二期可设为 `false` 并用 Redis/RQ worker 异步跑 `app.workers.jobs.run_parse_floorplan_job`。
- Mock render 是本地 SVG，占位展示概念效果；真实图片生成封装在 `openai_service.generate_interior_image()`。
- 布局规则覆盖常见客厅、卧室、餐厨、卫生间占位；二期可加入窗前避让、动线图、更多家具模板。
- 生活方案包的价格带是本地经验规则，占位用于产品闭环；上线前应接入授权家具/材料价格库，并按城市和品牌层级校正。
- 本项目不输出施工图，不判断承重墙，不做结构安全结论。
- 如果使用网页 Key 或网页模型覆盖且 `SYNC_JOBS=false`，异步 worker 不能读取浏览器请求头；worker 场景请把 Key 和默认模型放到 `.env`。

## OpenAI API 使用位置

所有 OpenAI 相关调用只允许出现在：

```text
apps/api/app/services/openai_service.py
```

已保留函数：

- `analyze_floorplan_image(image_path)`
- `parse_design_brief(user_text)`
- `build_render_prompt(floorplan, layout_option, design_brief)`
- `review_design_options(project_id, floorplan, layout_options, design_brief)`
- `generate_interior_image(prompt, reference_image_path=None)`

没有 `OPENAI_API_KEY` 时，上述函数全部使用 deterministic mock，保证测试和本地演示可跑。

前端 Key 入口：

```text
apps/web/components/OpenAIKeyPanel.tsx
```

后端状态接口：

```text
GET /api/settings/openai
```
