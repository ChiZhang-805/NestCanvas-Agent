# NestCanvas Agent 操作手册

本文面向演示者、测试用户和后续运营维护人员，说明如何启动、使用、演示和维护 NestCanvas Agent（栖画）。

## 1. 产品定位

NestCanvas 是面向买房、租房、装修用户的 C 端 AI 家居设计画布。

核心流程是：

1. 上传户型图、空房照片、售楼册截图或 PDF。
2. 整理图片并解析为可校正的户型底图。
3. 用自然语言写生活方式需求。
4. 生成多套家具布局并比较风险。
5. 生成采购清单、家庭沟通建议和概念渲染。
6. 导出结构化项目 JSON，给家人、设计师或销售沟通。

重要边界：

- OpenAI 负责语义理解、视觉说明、概念 prompt 和图片生成。
- 家具坐标、碰撞、挡门、通道和评分由本地规则引擎计算。
- 当前版本不是施工图工具，不判断承重墙，不输出结构安全结论。

## 2. 快速启动

本地启动后端：

```bash
cd /home/chi/Project/NestCanvas-Agent
cp .env.example .env
cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

本地启动前端：

```bash
cd /home/chi/Project/NestCanvas-Agent/apps/web
npm install
NESTCANVAS_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

打开：

```text
http://localhost:3000
```

生产构建检查：

```bash
cd /home/chi/Project/NestCanvas-Agent/apps/web
npm run typecheck
npm run lint
npm run build
```

后端测试：

```bash
cd /home/chi/Project/NestCanvas-Agent
python -m pytest apps/api/tests -q
```

## 3. Render 使用

Render Blueprint 文件位于仓库根目录：

```text
render.yaml
```

Blueprint 会创建：

- `nestcanvas-api`：FastAPI 后端。
- `nestcanvas-web`：Next.js 前端。

默认情况下，用户访问 `nestcanvas-web` 的公开网址即可使用。前端通过服务端代理访问 API：

```env
NESTCANVAS_API_BASE_URL=https://nestcanvas-api.onrender.com
```

Render Free plan 可能休眠。首次打开慢、长时间无访问后再次打开慢，通常是实例冷启动，不一定是代码错误。若页面显示 API 连接错误，优先检查：

1. `nestcanvas-api` 服务是否启动成功。
2. `nestcanvas-web` 的 `NESTCANVAS_API_BASE_URL` 是否指向正确 API 地址。
3. API 健康检查 `/healthz` 是否返回正常。

## 4. OpenAI Key 和模型设置

网页端的 OpenAI 设置入口在：

- 首页右侧快速面板。
- 项目内部页面顶部的 `OpenAI API Key` 面板。

可配置项：

- `OpenAI API Key`
- 解释模型
- 快速模型
- 图片模型

默认下拉候选以页面为准。当前代码中包含：

- 解释模型：`gpt-5.5`、`gpt-5.4`、`gpt-5.4-mini`、`gpt-5.4-nano`、`gpt-4.1`
- 快速模型：`gpt-5.4-mini`、`gpt-5.4-nano`、`gpt-5.4`、`gpt-5.5`
- 图片模型：`gpt-image-2`、`gpt-image-1.5`、`gpt-image-1-mini`
- 自定义模型 ID

保存规则：

- Key 和模型选择只保存在当前浏览器 `localStorage`。
- 后端不会把网页输入的 Key 写入数据库、文件或 Render。
- 调用 API 时，前端通过请求头临时发送：
  - `X-OpenAI-API-Key`
  - `X-OpenAI-Model-Text`
  - `X-OpenAI-Model-Fast`
  - `X-OpenAI-Model-Image`

无 Key 时系统会进入 mock 模式，仍可完整演示流程。

## 5. 推荐演示路径

### 5.1 快速演示

1. 打开首页。
2. 点击 `校正户型`、`填写需求`、`生成方案` 或 `查看渲染`。
3. 系统会创建 demo 项目并跳到对应步骤。
4. 在项目页顶部查看 OpenAI 状态。
5. 浏览户型、需求、方案、清单、助手和渲染页。

适合 3 到 5 分钟演示。

### 5.2 真实用户路径

1. 首页输入项目名称。
2. 点击 `开始创作` 或 `上传资产`。
3. 在上传页选择图片、PDF 或售楼册截图。
4. 点击输入整理，检查整理前后图。
5. 进入户型页，生成草稿底图或解析真实图片。
6. 校正墙体、房间、门窗、比例。
7. 进入需求页，用自然语言描述预算、风格、家庭成员、收纳、生活习惯和禁忌。
8. 进入方案页生成多套家具布局。
9. 查看碰撞、挡门、通道、收纳和生活方式适配。
10. 进入清单页生成预算分期和采购优先级。
11. 进入助手页生成家庭沟通卡和设计师交接问题。
12. 进入渲染页生成概念图。
13. 导出项目 JSON。

## 6. 页面说明

### 上传

用途：上传图片、PDF、售楼册截图或房间照片。

建议输入：

- 清晰户型图。
- 售楼册平面页截图。
- 空房照片。
- 暂无图片时，可先使用无图兜底草稿。

注意：

- 图片整理会做裁剪、透视拉正、对比度增强和线条锐化。
- 低质量素材会降低户型解析置信度，后续需人工校正。

### 户型库

用途：从内置种子模板中检索相似户型，并写入项目。

可筛选字段：

- 关键词
- 卧室数
- 面积范围
- 数据集来源
- 标签

运营维护时，应为每条模板保留 `source_license` 和来源说明。

### 户型

用途：查看和校正 `FloorPlan JSON`。

重点检查：

- 房间名称和面积是否合理。
- 门窗位置是否基本正确。
- 主要家具是否没有明显挡门或穿墙。
- 户型比例是否符合真实尺度。

### 需求

用途：把自然语言生活需求转为结构化 brief。

建议让用户写：

- 家庭成员。
- 预算区间。
- 风格偏好。
- 收纳重点。
- 宠物、儿童、老人等特殊需求。
- 禁忌项，例如不要开放厨房、不要过多玻璃、不要难打理材料。

### 方案

用途：生成和比较多套家具布局。

重点看：

- 总评分。
- 碰撞数量。
- 挡门风险。
- 通道和动线。
- 收纳能力。
- 生活方式匹配。

### 清单

用途：把最佳方案转成可执行采购和预算计划。

适合输出给：

- 家人讨论。
- 软装顾问。
- 设计师。
- 家具门店销售。

### 助手

用途：生成家庭教练包。

包含：

- 逐房间建议。
- 量尺任务。
- 采购重点。
- 家庭沟通脚本。
- 设计师交接问题。

### 渲染

用途：生成概念效果图和渲染 prompt。

注意：

- 渲染图只表达概念氛围。
- 最终落地仍需回到户型、尺寸、预算和材料库校验。

## 7. 数据库和检索库维护

NestCanvas 后续应维护四类检索库。

### 7.1 户型检索库

字段建议：

```text
id
name
area_m2
bedrooms
bathrooms
room_types
tags
floorplan_json
preview_image
source_name
source_license
source_url
created_at
updated_at
```

推荐处理流程：

1. 下载或接入授权数据。
2. 转为统一 `FloorPlan JSON`。
3. 提取面积、房间数、房间类型、标签。
4. 生成预览图。
5. 建立关键词和结构化字段索引。
6. 前端 `/library` 检索并写入项目。

### 7.2 家具尺寸库

字段建议：

```text
category
name
width_mm
depth_mm
height_mm
price_band
style_tags
material_tags
brand
source_license
```

用途：

- 让家具布局不再只用固定占位尺寸。
- 为采购清单生成更真实的价格和尺寸建议。

### 7.3 材料和软装价格库

字段建议：

```text
material_type
name
unit
price_low
price_high
durability
maintenance_level
style_tags
city
source_license
```

用途：

- 预算分期。
- 材料替代建议。
- 风格和维护难度提醒。

### 7.4 视觉和布局研究库

可用于训练或评估：

- 家具组合关系。
- 风格搭配。
- 房间语义识别。

注意许可：

- 研究数据和非商业许可数据不能直接放进商用素材库。
- 生产前必须保留来源、授权和可再分发证明。

## 8. 常见故障处理

### 页面打开慢

可能原因：

- Render Free plan 冷启动。
- 浏览器首次加载 Next.js bundle。
- API 服务刚被唤醒。

处理：

1. 等待 30 到 90 秒。
2. 刷新页面。
3. 检查 API `/healthz`。
4. Render 后台看最近日志。

### Internal Server Error

处理顺序：

1. 打开 Render API 日志。
2. 看是否缺少环境变量或存储目录权限。
3. 本地运行 `python -m pytest apps/api/tests -q`。
4. 本地运行 `npm run build`。
5. 检查前端 API 代理变量 `NESTCANVAS_API_BASE_URL`。

### OpenAI 不生效

检查：

1. 网页面板是否保存了 Key。
2. 状态是否显示 `浏览器设置` 或 `.env Key`。
3. 模型 ID 是否为空。
4. 浏览器是否禁用了 localStorage。
5. 后端日志是否显示 OpenAI 调用异常。

无 Key 或调用失败时会自动 fallback 到 mock。

### 页面出现横向滚动

本项目设计要求：

- 页面根节点不出现横向滚动。
- 长内容放在模块内部纵向滚动。
- 小屏避免表格横向滚动。

检查方式：

1. 用 390px 宽移动端视口打开首页和项目页。
2. 检查浏览器底部是否出现横向滚动。
3. 检查卡片、按钮、项目 ID 和长文本是否换行。
4. 新增表格时优先改为卡片列表。

## 9. 上线前检查清单

每次改完功能后至少运行：

```bash
cd /home/chi/Project/NestCanvas-Agent
python -m pytest apps/api/tests -q

cd /home/chi/Project/NestCanvas-Agent/apps/web
npm run typecheck
npm run lint
npm run build
```

浏览器检查：

- 首页桌面和移动端无根级滚动条。
- 项目页只有内容模块内部纵向滚动。
- 无横向滚动。
- 无明显文本重叠。
- OpenAI Key 清除后能回到 mock。
- 上传、户型、需求、方案、清单、助手、渲染至少各打开一次。

## 10. 运营建议

- 公共 demo 默认不放站主 Key，让用户自己在浏览器填写。
- 演示前准备一组清晰户型图和一组低质量截图，展示输入整理能力。
- 不要承诺施工可落地性；表述为“概念方案、沟通草案、预算初筛”。
- 商用前优先补强户型解析、家具尺寸库、材料价格库和许可管理。
