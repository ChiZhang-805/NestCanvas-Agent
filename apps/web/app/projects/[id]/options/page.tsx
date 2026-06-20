"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ClipboardList, ImageIcon, RefreshCw, Sparkles } from "lucide-react";
import { FloorPlanSvg } from "@/components/FloorPlanSvg";
import { PageShell } from "@/components/PageShell";
import { createDesignReview, createLayoutOptions, getProject } from "@/lib/api";
import { DesignReview, FloorPlan, LayoutOption, ProjectDetail } from "@/lib/types";

export default function OptionsPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [review, setReview] = useState<DesignReview | null>(null);
  const [busy, setBusy] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    async function loadProject() {
      setError(null);
      setProject(null);
      setReview(null);
      setSelectedId(null);
      setReviewBusy(false);

      const loaded = await getProject(projectId);
      if (!isCurrent) {
        return;
      }
      setProject(loaded);

      if (loaded.layout_options.length === 0) {
        return;
      }

      const fallbackId = loaded.layout_options[0]?.id ?? null;
      setSelectedId(fallbackId);
      setReviewBusy(true);
      try {
        const loadedReview = await createDesignReview(projectId);
        if (!isCurrent) {
          return;
        }
        setReview(loadedReview);
        setSelectedId(loadedReview.best_option_id ?? fallbackId);
      } finally {
        if (isCurrent) {
          setReviewBusy(false);
        }
      }
    }

    loadProject().catch((caught) => {
      if (isCurrent) {
        setError(caught instanceof Error ? caught.message : "加载失败");
      }
    });

    return () => {
      isCurrent = false;
    };
  }, [projectId]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const options = await createLayoutOptions(projectId);
      setSelectedId(options[0]?.id ?? null);
      setProject((current) =>
        current ? { ...current, layout_options: options } : current
      );
      setReview(await createDesignReview(projectId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "生成方案失败");
    } finally {
      setBusy(false);
    }
  }

  const floorplan: FloorPlan | null = project?.floorplans.at(-1) ?? null;
  const options: LayoutOption[] = project?.layout_options ?? [];
  const selected = options.find((option) => option.id === selectedId) ?? options[0] ?? null;
  const selectedReview =
    review?.option_reviews.find((item) => item.option_id === selected?.id) ??
    review?.option_reviews[0] ??
    null;
  const bestReview = review?.option_reviews.find((item) => item.option_id === review.best_option_id);

  return (
    <PageShell projectId={projectId} current="options" title="布局方案对比">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={generate}
          disabled={busy}
          className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white disabled:opacity-60"
        >
          <RefreshCw size={17} aria-hidden="true" />
          {busy ? "生成中" : "生成 3 套方案"}
        </button>
        <Link
          href={`/projects/${projectId}/living`}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink"
        >
          <ClipboardList size={17} aria-hidden="true" />
          清单
        </Link>
        <Link
          href={`/projects/${projectId}/renders`}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink"
        >
          <ImageIcon size={17} aria-hidden="true" />
          渲染
        </Link>
        <button
          type="button"
          onClick={async () => {
            setReviewBusy(true);
            setError(null);
            try {
              setReview(await createDesignReview(projectId));
            } catch (caught) {
              setError(caught instanceof Error ? caught.message : "设计评审失败");
            } finally {
              setReviewBusy(false);
            }
          }}
          disabled={reviewBusy || options.length === 0}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink disabled:opacity-60"
        >
          <Sparkles size={17} aria-hidden="true" />
          {reviewBusy ? "评审中" : "设计评审"}
        </button>
        {error && <span className="text-sm text-clay">{error}</span>}
      </div>
      {selected ? (
        <div className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
          <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase text-clay">Selected layout</p>
                <h2 className="mt-1 text-xl font-semibold text-ink">{selected.strategy}</h2>
              </div>
              <span className="rounded-md bg-ink px-3 py-2 text-sm font-bold text-white">
                Score {selected.score}
              </span>
            </div>
            <FloorPlanSvg floorplan={floorplan} option={selected} />
            {selectedReview && (
              <section className="mt-4 rounded-md border border-ink/10 bg-cloud p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase text-clay">Design review</p>
                    <h3 className="mt-1 text-lg font-bold text-ink">{selectedReview.headline}</h3>
                  </div>
                  <span className="rounded-md bg-white px-3 py-2 text-sm font-bold text-ink">
                    综合 {selectedReview.scores.composite ?? selected.score}
                  </span>
                </div>
                <div className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
                  {Object.entries(selectedReview.scores).map(([name, score]) => (
                    <div key={name} className="rounded-md bg-white p-3">
                      <div className="flex items-center justify-between gap-3">
                        <span className="font-semibold text-ink/70">{name}</span>
                        <span className="font-black text-ink">{Math.round(score)}</span>
                      </div>
                      <div className="mt-2 h-1.5 rounded bg-ink/10">
                        <div
                          className="h-1.5 rounded bg-tide"
                          style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </section>

          <section className="space-y-3">
            {review && (
              <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase text-clay">
                      {review.generated_with === "openai" ? "OpenAI design agent" : "Local design rules"}
                    </p>
                    <h2 className="mt-1 text-lg font-bold text-ink">设计顾问结论</h2>
                  </div>
                  <span className="rounded-md bg-ink px-3 py-2 text-sm font-black text-white">
                    {Math.round(review.readiness_score)}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-6 text-ink/72">{review.summary}</p>
                {bestReview && (
                  <p className="mt-3 rounded-md bg-flax px-3 py-2 text-sm font-bold text-ink">
                    主推：{bestReview.strategy}
                  </p>
                )}
                {review.global_risks.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {review.global_risks.slice(0, 3).map((risk) => (
                      <p key={risk} className="flex gap-2 text-sm text-clay">
                        <AlertTriangle size={16} className="mt-0.5 shrink-0" aria-hidden="true" />
                        {risk}
                      </p>
                    ))}
                  </div>
                )}
                {review.next_questions.length > 0 && (
                  <div className="mt-4 rounded-md border border-ink/10 p-3">
                    <p className="text-sm font-bold text-ink">下一步要问清楚</p>
                    <div className="mt-2 space-y-1 text-sm text-ink/68">
                      {review.next_questions.map((question) => (
                        <p key={question}>{question}</p>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            )}
            {options.map((option) => (
              <button
                key={option.id}
                type="button"
                onClick={() => setSelectedId(option.id)}
                className={`focus-ring w-full rounded-md border p-4 text-left shadow-panel transition ${
                  option.id === selected.id
                    ? "border-ink bg-ink text-white"
                    : "border-ink/10 bg-white text-ink hover:border-ink/35"
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-semibold">{option.strategy}</span>
                  <span className="text-sm font-bold">{option.score}</span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-xs font-semibold opacity-80">
                  <span>硬错误 {option.hard_errors.length}</span>
                  <span>软风险 {option.soft_warnings.length}</span>
                </div>
                {option.soft_warnings[0] && (
                  <p className="mt-3 text-sm opacity-75">{option.soft_warnings[0]}</p>
                )}
                {review?.best_option_id === option.id && (
                  <p className="mt-3 inline-flex items-center gap-2 text-sm font-bold">
                    <CheckCircle2 size={15} aria-hidden="true" />
                    当前主推
                  </p>
                )}
              </button>
            ))}
            {selectedReview && (
              <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
                <p className="text-sm font-bold text-ink">当前方案建议</p>
                <div className="mt-3 space-y-3 text-sm leading-6 text-ink/70">
                  {selectedReview.strengths.map((item) => (
                    <p key={item}>优势：{item}</p>
                  ))}
                  {selectedReview.concerns.map((item) => (
                    <p key={item}>风险：{item}</p>
                  ))}
                  {selectedReview.suggestions.map((item) => (
                    <p key={item}>建议：{item}</p>
                  ))}
                </div>
              </section>
            )}
          </section>
        </div>
      ) : (
        <section className="rounded-md border border-ink/10 bg-white p-5 text-sm text-ink/65 shadow-panel">
          暂无布局方案。
        </section>
      )}
    </PageShell>
  );
}
