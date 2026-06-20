"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, KeyRound, RefreshCw, Trash2 } from "lucide-react";
import {
  getOpenAISettingsStatus,
  getStoredOpenAIKey,
  saveStoredOpenAIKey
} from "@/lib/api";
import { OpenAISettingsStatus } from "@/lib/types";

function sourceLabel(status: OpenAISettingsStatus | null) {
  if (!status) return "检测中";
  if (status.source === "browser") return "浏览器 Key";
  if (status.source === "env") return ".env Key";
  return "Mock 模式";
}

export function OpenAIKeyPanel({ compact = false }: { compact?: boolean }) {
  const [value, setValue] = useState("");
  const [status, setStatus] = useState<OpenAISettingsStatus | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function refreshStatus() {
    try {
      setStatus(await getOpenAISettingsStatus());
    } catch {
      setStatus(null);
    }
  }

  useEffect(() => {
    setValue(getStoredOpenAIKey());
    refreshStatus();
  }, []);

  function save() {
    saveStoredOpenAIKey(value);
    setMessage(value.trim() ? "已保存到本机浏览器" : "已切换为环境变量或 mock");
    refreshStatus();
  }

  function clear() {
    setValue("");
    saveStoredOpenAIKey("");
    setMessage("已清除浏览器 Key");
    refreshStatus();
  }

  return (
    <section
      className={`rounded-md border border-ink/10 bg-white/78 text-ink shadow-panel backdrop-blur ${
        compact ? "p-3" : "p-4"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 text-xs font-black uppercase text-clay">
            <KeyRound size={14} aria-hidden="true" />
            OpenAI API Key
          </p>
          <p className="mt-1 text-sm font-semibold text-ink/70">
            当前：{sourceLabel(status)}
          </p>
        </div>
        <button
          type="button"
          onClick={refreshStatus}
          className="focus-ring rounded-md border border-ink/10 p-2 text-ink/70 transition hover:text-ink"
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

      {!compact && (
        <p className="mt-2 text-xs font-medium leading-5 text-ink/55">
          Key 只保存在当前浏览器 localStorage，调用需求抽取和概念渲染时通过请求头发送到本机 API。
        </p>
      )}
      {message && <p className="mt-2 text-xs font-bold text-tide">{message}</p>}
      {status && (
        <p className="mt-2 text-xs text-ink/48">
          text {status.text_model} · image {status.image_model}
        </p>
      )}
    </section>
  );
}
