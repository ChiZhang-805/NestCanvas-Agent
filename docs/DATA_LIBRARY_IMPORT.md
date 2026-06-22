# NestCanvas 检索库导入方案

## 当前数据

当前 `/api/floorplan-library` 有 6 个内部结构化 seed 户型，可直接在“检索户型库”页面检索、预览、写入项目。

本轮已新增 manifest 扩展能力：把小样本写入 `apps/api/app/data/floorplan_library/manifest.json` 后，后端会自动合并检索。缩略图放在 `apps/api/app/data/floorplan_library/assets/`，通过 `/library-assets/floorplans/...` 访问。

## 建议先接的数据

1. CubiCasa5K

- 官方数据约 5.5GB，包含 5000 张户型图和语义标注。
- 适合做“图像式户型检索”和视觉解析验证。
- 不建议把完整 zip 放进 GitHub；先下载到 `data/raw/cubicasa5k/`，抽 100 张压缩图和结构化结果进 manifest。

2. Swiss Dwellings

- 更偏结构化几何和居住性能指标。
- 适合扩展筛选条件：采光、噪声、房间拓扑、位置特征。
- 可作为 NestCanvas 后续“推荐理由”和“相似户型解释”的强数据源。

3. 家具尺寸库与材料价格库

- 用于从“户型像不像”升级到“这个家是否能住、能买、能落地”。
- 建议字段：品类、长宽高、最小通行间距、价格区间、适用房间、风格标签。

## 导入流程

1. 把原始数据下载到仓库根目录：

```bash
mkdir -p data/raw/cubicasa5k
```

2. 抽取小样本：

- 选择 100 个样本。
- 图片压缩到 800px 宽以内。
- 如果已有标注，转换为 `FloorPlan` JSON。
- 没有结构化标注时，先用低置信度 boundary 占位，后续再用视觉解析补齐。

3. 写入产品目录：

```text
apps/api/app/data/floorplan_library/
  manifest.json
  assets/
    sample_0001.png
```

4. 刷新网页：

- 打开项目内“检索户型库”。
- 用卧室数、面积、关键词筛选。
- 选中卡片后写入项目，再去“校正 2D 户型”检查。

## 后续可加的大模型能力

- Vision：从原始户型图识别房间、门窗、朝向和文字标注。
- Text reasoning：把用户自然语言需求扩展为检索标签，例如“一家三口 + 老人偶住”扩展为 `two_bedroom`、`guest_room`、`storage`。
- Similarity rerank：先用结构化条件召回，再让模型解释“为什么这个户型更适合”。
- Batch curator：批量检查外部样本是否缺字段、面积异常、房间闭合失败。
