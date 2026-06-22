export type OpenAIModelOption = {
  value: string;
  label: string;
  description: string;
};

export const CUSTOM_MODEL_VALUE = "__custom_openai_model__";

export const TEXT_MODEL_OPTIONS: OpenAIModelOption[] = [
  {
    value: "gpt-5.5",
    label: "gpt-5.5",
    description: "推荐：需求解释、方案复核"
  },
  {
    value: "gpt-5.4",
    label: "gpt-5.4",
    description: "均衡：质量较高，成本低于 flagship"
  },
  {
    value: "gpt-5.4-mini",
    label: "gpt-5.4-mini",
    description: "更快：适合日常文本任务"
  },
  {
    value: "gpt-5.4-nano",
    label: "gpt-5.4-nano",
    description: "最低成本：适合轻量抽取"
  },
  {
    value: "gpt-4.1",
    label: "gpt-4.1",
    description: "非推理备选：文本稳定，推理能力较弱"
  }
];

export const FAST_MODEL_OPTIONS: OpenAIModelOption[] = [
  {
    value: "gpt-5.4-mini",
    label: "gpt-5.4-mini",
    description: "推荐：户型视觉识别、轻量解析"
  },
  {
    value: "gpt-5.4-nano",
    label: "gpt-5.4-nano",
    description: "更低成本：简单识别"
  },
  {
    value: "gpt-5.4",
    label: "gpt-5.4",
    description: "更稳：复杂户型图"
  },
  {
    value: "gpt-5.5",
    label: "gpt-5.5",
    description: "最高质量：慢一些，成本更高"
  }
];

export const IMAGE_MODEL_OPTIONS: OpenAIModelOption[] = [
  {
    value: "gpt-image-2",
    label: "gpt-image-2",
    description: "推荐：室内概念图质量优先"
  },
  {
    value: "gpt-image-1.5",
    label: "gpt-image-1.5",
    description: "备选：兼容上一代图片生成"
  },
  {
    value: "gpt-image-1-mini",
    label: "gpt-image-1-mini",
    description: "更低成本：快速概念草图"
  }
];

export function modelSelectValue(value: string, options: OpenAIModelOption[]) {
  return options.some((option) => option.value === value) ? value : CUSTOM_MODEL_VALUE;
}

export function modelDescription(value: string, options: OpenAIModelOption[]) {
  return options.find((option) => option.value === value)?.description ?? "自定义模型 ID";
}
