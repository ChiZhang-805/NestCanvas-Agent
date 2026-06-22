# NestCanvas Floorplan Library Data

这个目录用于放真正进入产品检索库的小样本数据。

当前状态：
- 后端默认提供 6 个内部结构化 seed 户型。
- 如果本目录存在 `manifest.json`，后端会自动把其中的 items 合并进 `/api/floorplan-library`。
- `assets/` 会通过 API 挂载到 `/library-assets/floorplans/`，可用于 manifest 里的 `preview_image_url`。

推荐目录结构：

```text
apps/api/app/data/floorplan_library/
  manifest.json
  assets/
    cubicasa_sample_0001.png
    swiss_dwelling_0001.png
```

`manifest.json` 格式：

```json
{
  "items": [
    {
      "id": "cubicasa_0001",
      "title": "CubiCasa sample 0001",
      "source_dataset_id": "cubicasa5k",
      "area_m2": 72,
      "bedrooms": 2,
      "bathrooms": 1,
      "region": "external",
      "tags": ["two_bedroom", "family", "retrieval_sample"],
      "household_fit": ["一家三口"],
      "preview_image_url": "/library-assets/floorplans/cubicasa_sample_0001.png",
      "preview_kind": "image",
      "floorplan": {
        "version": "1.0",
        "unit": "m",
        "scale_m_per_px": 0.025,
        "boundary": [[0, 0], [8, 0], [8, 9], [0, 9], [0, 0]],
        "rooms": [],
        "walls": [],
        "doors": [],
        "windows": [],
        "warnings": ["External sample needs calibration."],
        "confidence": 0.3
      }
    }
  ]
}
```

注意：
- 大型原始下载不要放在这里，放到仓库根目录的 `data/raw/` 或 `data/external/`，这些路径已被 `.gitignore` 忽略。
- 这个目录只放要跟随 GitHub/Render 部署的小体量样本，例如 100 张压缩缩略图和对应 manifest。
