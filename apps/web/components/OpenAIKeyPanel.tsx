"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, KeyRound, RefreshCw, Trash2 } from "lucide-react";
import {
  getOpenAISettingsStatus,
  getStoredOpenAISettings,
  saveStoredOpenAISettings
} from "@/lib/api";
import {
  CUSTOM_MODEL_VALUE,
  FAST_MODEL_OPTIONS,
  IMAGE_MODEL_OPTIONS,
  OpenAIModelOption,
  TEXT_MODEL_OPTIONS,
  modelDescription,
  modelSelectValue
} from "@/lib/openaiModels";
import { OpenAISettingsStatus } from "@/lib/types";

function ModelSelect({
  label,
  value,
  options,
  onChange,
  showDescription = true,
  className = ""
}: {
  label: string;
  value: string;
  options: OpenAIModelOption[];
  onChange: (value: string) => void;
  showDescription?: boolean;
  className?: string;
}) {
  const selected = modelSelectValue(value, options);

  return (
    <label className={`grid gap-1 text-xs font-black uppercase tracking-wide text-ink/55 ${className}`}>
      <span>{label}</span>
      <select
        className="focus-ring min-h-10 min-w-0 rounded-md border border-ink/15 bg-white px-2 text-sm font-bold normal-case tracking-normal text-ink"
        value={selected}
        title={value}
        onChange={(event) => onChange(event.target.value === CUSTOM_MODEL_VALUE ? "" : event.target.value)}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
        <option value={CUSTOM_MODEL_VALUE}>自定义模型 ID</option>
      </select>
      {selected === CUSTOM_MODEL_VALUE ? (
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="例如 gpt-5.5"
          spellCheck={false}
          autoComplete="off"
          className="focus-ring min-h-10 min-w-0 rounded-md border border-ink/15 bg-white px-2 text-sm font-semibold normal-case tracking-normal text-ink"
        />
      ) : showDescription ? (
        <span className="text-[11px] font-semibold normal-case leading-4 tracking-normal text-ink/48">
          {modelDescription(value, options)}
        </span>
      ) : (
        <span className="sr-only">{modelDescription(value, options)}</span>
      )}
    </label>
  );
}

export function OpenAIKeyPanel({ compact = false }: { compact?: boolean }) {
  const [value, setValue] = useState("");
  const [modelText, setModelText] = useState("gpt-5.5");
  const [modelFast, setModelFast] = useState("gpt-5.4-mini");
  const [modelImage, setModelImage] = useState("gpt-image-2");
  const [status, setStatus] = useState<OpenAISettingsStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const hasBrowserKey = value.trim().length > 0;

  async function refreshStatus() {
    try {
      const next = await getOpenAISettingsStatus();
      const stored = getStoredOpenAISettings();
      setStatus(next);
      setModelText(stored.modelText || next.text_model);
      setModelFast(stored.modelFast || next.fast_model);
      setModelImage(stored.modelImage || next.image_model);
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    const stored = getStoredOpenAISettings();
    setValue(stored.apiKey);
    setModelText(stored.modelText || "gpt-5.5");
    setModelFast(stored.modelFast || "gpt-5.4-mini");
    setModelImage(stored.modelImage || "gpt-image-2");
    refreshStatus();
  }, []);

  function save() {
    const cleanedModelText = modelText.trim();
    const cleanedModelFast = modelFast.trim();
    const cleanedModelImage = modelImage.trim();
    if (!cleanedModelText || !cleanedModelFast || !cleanedModelImage) {
      setMessage("请先选择或填写完整模型 ID");
      return;
    }
    saveStoredOpenAISettings({
      apiKey: value,
      modelText: cleanedModelText,
      modelFast: cleanedModelFast,
      modelImage: cleanedModelImage
    });
    setMessage(value.trim() ? "已保存到本机浏览器" : "已切换为环境变量或 mock");
    refreshStatus();
  }

  function clear() {
    setValue("");
    setModelText(status?.text_model || "gpt-5.5");
    setModelFast(status?.fast_model || "gpt-5.4-mini");
    setModelImage(status?.image_model || "gpt-image-2");
    saveStoredOpenAISettings({ apiKey: "", modelText: "", modelFast: "", modelImage: "" });
    setMessage("已清除浏览器 OpenAI 设置");
    refreshStatus();
  }

  return (
    <section
      className={`rounded-md border border-ink/10 bg-white/78 text-ink shadow-panel backdrop-blur ${
        compact ? "p-3" : "p-4"
      }`}
    >
      <div className="flex min-h-10 items-center justify-between gap-3">
        <div className="min-w-0">
          <p className={`flex items-center gap-2 text-sm font-black uppercase leading-none ${hasBrowserKey ? "text-tide" : "text-clay"}`}>
            <KeyRound size={14} aria-hidden="true" />
            OpenAI API Key
          </p>
        </div>
        <button
          type="button"
          onClick={refreshStatus}
          className="focus-ring flex size-10 shrink-0 items-center justify-center rounded-md border border-ink/10 text-ink/70 transition hover:text-ink"
          aria-label="刷新 OpenAI 状态"
        >
          <RefreshCw size={15} aria-hidden="true" />
        </button>
      </div>

      <div className="mt-3 flex gap-2">
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          type="password"
          spellCheck={false}
          autoComplete="off"
          placeholder="sk-..."
          className="focus-ring min-h-10 min-w-0 flex-1 rounded-md border border-ink/15 bg-white px-3 text-sm font-semibold"
        />
        <button
          type="button"
          onClick={save}
          className="focus-ring inline-flex items-center gap-2 rounded-md bg-ink px-3 text-sm font-bold text-white transition hover:bg-tide"
        >
          <CheckCircle2 size={15} aria-hidden="true" />
          保存
        </button>
        {!compact && (
          <button
            type="button"
            onClick={clear}
            className="focus-ring rounded-md border border-ink/15 px-3 text-ink/70 transition hover:text-ink"
          >
            <Trash2 size={15} aria-hidden="true" />
          </button>
        )}
      </div>

      <div className={`mt-3 grid gap-2 ${compact ? "grid-cols-1 sm:grid-cols-2" : "md:grid-cols-3"}`}>
        <ModelSelect
          label="解释模型"
          value={modelText}
          options={TEXT_MODEL_OPTIONS}
          onChange={setModelText}
          showDescription={!compact}
        />
        <ModelSelect
          label="快速模型"
          value={modelFast}
          options={FAST_MODEL_OPTIONS}
          onChange={setModelFast}
          showDescription={!compact}
        />
        <ModelSelect
          label="图片模型"
          value={modelImage}
          options={IMAGE_MODEL_OPTIONS}
          onChange={setModelImage}
          showDescription={!compact}
          className={compact ? "sm:col-span-2" : ""}
        />
      </div>

      {!compact && (
        <p className="mt-2 text-xs font-medium leading-5 text-ink/55">
          Key 和模型只保存在当前浏览器 localStorage，调用需求抽取、户型识别和概念渲染时通过请求头发送到本机 API。
        </p>
      )}
      {message && <p className="mt-2 text-xs font-bold text-tide">{message}</p>}
    </section>
  );
}
