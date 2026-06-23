"use client";

import Link from "next/link";
import { ArrowLeft, Home, WandSparkles } from "lucide-react";
import { OpenAIKeyPanel } from "@/components/OpenAIKeyPanel";

export default function SettingsPage() {
  return (
    <main className="min-h-[100svh] bg-[#f2f4f1] px-5 py-6 text-ink">
      <header className="mx-auto flex max-w-[1180px] flex-wrap items-center justify-between gap-3">
        <Link href="/" className="focus-ring inline-flex items-center gap-3 rounded-md text-ink">
          <span className="flex size-10 items-center justify-center rounded-md border border-tide/20 bg-tide/10 text-tide">
            <WandSparkles size={20} aria-hidden="true" />
          </span>
          <span className="text-sm font-black leading-tight">
            NestCanvas Agent
            <br />
            设置
          </span>
        </Link>
        <Link
          href="/"
          className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-md border border-ink/10 bg-white px-3 py-2 text-sm font-bold text-ink transition hover:border-tide"
        >
          <Home size={16} aria-hidden="true" />
          首页
        </Link>
      </header>

      <section className="mx-auto mt-8 max-w-[1180px]">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-black leading-tight sm:text-4xl">OpenAI 设置</h1>
            <p className="mt-2 text-sm font-semibold leading-6 text-ink/62">
              API Key 和模型只保存在当前浏览器，用于需求抽取、户型识别和概念渲染。
            </p>
          </div>
          <Link
            href="/"
            className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-md border border-ink/10 bg-white px-3 py-2 text-sm font-bold text-ink transition hover:border-tide"
          >
            <ArrowLeft size={16} aria-hidden="true" />
            返回
          </Link>
        </div>
        <OpenAIKeyPanel />
      </section>
    </main>
  );
}
