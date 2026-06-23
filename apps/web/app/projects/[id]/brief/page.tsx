"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, MessageSquareText, Send } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { createBrief, getProject } from "@/lib/api";
import { notifyProjectUpdated } from "@/lib/projectEvents";
import { DesignBrief } from "@/lib/types";

export default function BriefPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [text, setText] = useState(
    "一家三口，喜欢温暖木色，需要大量收纳、一整面书柜和亲子活动区，预算20万，避免暗色。"
  );
  const [brief, setBrief] = useState<DesignBrief | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProject(projectId)
      .then((project) => {
        setBrief(project.briefs.at(-1) ?? null);
      })
      .catch((caught) => {
        setError(caught instanceof Error ? caught.message : "加载需求失败");
      });
  }, [projectId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setBrief(await createBrief(projectId, text));
      notifyProjectUpdated(projectId);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "需求抽取失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PageShell projectId={projectId} current="brief" title="结构化需求" currentStepReady={Boolean(brief)}>
      <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <form onSubmit={submit} className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
          <label className="flex items-center gap-2 text-sm font-medium text-ink" htmlFor="brief-text">
            <MessageSquareText size={17} aria-hidden="true" />
            生活方式 brief
          </label>
          <textarea
            id="brief-text"
            value={text}
            onChange={(event) => {
              setText(event.target.value);
              setBrief(null);
            }}
            rows={9}
            className="focus-ring mt-3 w-full resize-y rounded-md border border-ink/15 px-3 py-2 leading-7"
          />
          <button
            type="submit"
            disabled={busy}
            className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white disabled:opacity-60"
          >
            <Send size={17} aria-hidden="true" />
            {busy ? "抽取中" : "生成 DesignBrief"}
          </button>
          {error && <p className="mt-3 text-sm text-clay">{error}</p>}
        </form>
        <section className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
          {brief ? (
            <>
              <div className="flex flex-wrap gap-2">
                {[brief.style, brief.storage_level, ...(brief.color_palette ?? [])].map((item) => (
                  <span key={item} className="rounded-md bg-flax px-2 py-1 text-sm font-medium text-ink">
                    {item}
                  </span>
                ))}
              </div>
              <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="font-semibold text-ink">预算</dt>
                  <dd className="mt-1 text-ink/70">{brief.budget_cny ? `${brief.budget_cny} CNY` : "未设置"}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">居住者</dt>
                  <dd className="mt-1 text-ink/70">{brief.residents.join(", ")}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">必须有</dt>
                  <dd className="mt-1 text-ink/70">{brief.must_have.join(", ")}</dd>
                </div>
                <div>
                  <dt className="font-semibold text-ink">避免</dt>
                  <dd className="mt-1 text-ink/70">{brief.avoid.join(", ")}</dd>
                </div>
              </dl>
              <Link
                href={`/projects/${projectId}/options`}
                className="focus-ring mt-6 inline-flex items-center gap-2 rounded-md bg-ink px-4 py-2 font-semibold text-white"
              >
                生成方案
                <ArrowRight size={17} aria-hidden="true" />
              </Link>
            </>
          ) : (
            <p className="text-sm text-ink/65">暂无 DesignBrief。</p>
          )}
        </section>
      </div>
    </PageShell>
  );
}
