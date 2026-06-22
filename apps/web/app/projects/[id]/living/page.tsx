"use client";

import Link from "next/link";
import { AlertTriangle, CheckCircle2, ClipboardList, RefreshCw, Send, ShoppingBag } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { createLivingPlan } from "@/lib/api";
import { LivingPlanPackage, LivingShoppingItem } from "@/lib/types";

function money(value: number) {
  if (value >= 10000) return `${(value / 10000).toFixed(1)} 万`;
  return value.toLocaleString("zh-CN");
}

function priceRange(low: number, high: number) {
  return `${money(low)}-${money(high)}`;
}

function priorityLabel(priority: LivingShoppingItem["priority"]) {
  if (priority === "must_buy") return "必买";
  if (priority === "reuse_or_buy") return "复用/购买";
  return "可选";
}

function budgetFitLabel(value: LivingPlanPackage["budget_fit"]) {
  if (value === "within_budget") return "预算宽松";
  if (value === "tight") return "预算偏紧";
  if (value === "over_budget") return "可能超预算";
  return "待补预算";
}

function priorityClass(priority: LivingShoppingItem["priority"]) {
  if (priority === "must_buy") return "bg-ink text-white";
  if (priority === "reuse_or_buy") return "bg-flax text-ink";
  return "bg-cloud text-ink";
}

export default function LivingPlanPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [plan, setPlan] = useState<LivingPlanPackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setPlan(await createLivingPlan(projectId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "生活方案包生成失败");
    } finally {
      setBusy(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageShell projectId={projectId} current="living" title="生活方案清单">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={load}
          disabled={busy}
          className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white disabled:opacity-60"
        >
          <RefreshCw size={17} aria-hidden="true" />
          {busy ? "生成中" : "刷新清单"}
        </button>
        <Link
          href={`/projects/${projectId}/renders`}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink"
        >
          <Send size={17} aria-hidden="true" />
          去渲染
        </Link>
        {error && <span className="text-sm text-clay">{error}</span>}
      </div>

      {plan ? (
        <div className="grid gap-5">
          <section className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <p className="text-xs font-bold uppercase text-clay">Living package</p>
                <h2 className="mt-1 text-xl font-bold text-ink">{plan.selected_strategy}</h2>
                <p className="mt-3 text-sm leading-6 text-ink/70">{plan.household_summary}</p>
                <p className="mt-2 text-sm font-semibold leading-6 text-ink">{plan.recommended_next_step}</p>
              </div>
              <div className="rounded-md bg-ink px-4 py-3 text-right text-white">
                <p className="text-xs font-bold uppercase opacity-70">预算区间</p>
                <p className="mt-1 text-lg font-black">
                  {priceRange(plan.budget_total_low_cny, plan.budget_total_high_cny)}
                </p>
                <p className="mt-1 text-xs font-bold opacity-80">{budgetFitLabel(plan.budget_fit)}</p>
              </div>
            </div>
            {plan.caveats.length > 0 && (
              <div className="mt-4 grid gap-2">
                {plan.caveats.map((item) => (
                  <p key={item} className="flex gap-2 rounded-md bg-cloud px-3 py-2 text-sm text-ink/70">
                    <AlertTriangle size={15} className="mt-0.5 shrink-0 text-clay" aria-hidden="true" />
                    {item}
                  </p>
                ))}
              </div>
            )}
          </section>

          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {plan.budget_phases.map((phase) => (
              <div key={phase.key} className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
                <p className="text-xs font-bold uppercase text-clay">{phase.key}</p>
                <h3 className="mt-1 text-base font-bold text-ink">{phase.label}</h3>
                <p className="mt-3 text-lg font-black text-ink">
                  {priceRange(phase.estimated_budget_cny_min, phase.estimated_budget_cny_max)}
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {phase.included_categories.slice(0, 6).map((category) => (
                    <span key={category} className="rounded-md bg-cloud px-2 py-1 text-xs font-bold text-ink/70">
                      {category}
                    </span>
                  ))}
                </div>
                <div className="mt-3 grid gap-1 text-xs leading-5 text-ink/62">
                  {phase.notes.map((note) => (
                    <p key={note}>{note}</p>
                  ))}
                </div>
              </div>
            ))}
          </section>

          <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
            <div className="mb-3 flex items-center gap-2">
              <ShoppingBag size={18} className="text-tide" aria-hidden="true" />
              <h2 className="text-lg font-bold text-ink">采购优先级</h2>
            </div>
            <div className="grid gap-3">
              {plan.shopping_items.map((item, index) => (
                <article
                  key={`${item.room_id}-${item.category}-${index}`}
                  className="rounded-md border border-ink/8 bg-cloud/35 p-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0">
                      <h3 className="break-words text-sm font-bold text-ink">{item.label}</h3>
                      <p className="mt-1 text-xs font-semibold text-ink/58">{item.room_type}</p>
                    </div>
                    <span className={`shrink-0 rounded-md px-2 py-1 text-xs font-bold ${priorityClass(item.priority)}`}>
                      {priorityLabel(item.priority)}
                    </span>
                  </div>
                  <div className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
                    <div>
                      <p className="text-xs font-bold uppercase text-ink/45">尺寸</p>
                      <p className="mt-1 font-semibold text-ink/72">
                        {item.dimensions_m[0].toFixed(2)} x {item.dimensions_m[1].toFixed(2)} m
                      </p>
                    </div>
                    <div>
                      <p className="text-xs font-bold uppercase text-ink/45">预算</p>
                      <p className="mt-1 font-bold text-ink">{priceRange(item.estimated_price_cny_low, item.estimated_price_cny_high)}</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold uppercase text-ink/45">关键词</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {item.search_keywords.slice(0, 4).map((keyword) => (
                          <span key={keyword} className="rounded-md bg-white px-2 py-1 text-xs font-semibold text-ink/65">
                            {keyword}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <p className="mt-3 break-words text-sm leading-6 text-ink/68">{item.why}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
              <div className="mb-3 flex items-center gap-2">
                <ClipboardList size={18} className="text-tide" aria-hidden="true" />
                <h2 className="text-lg font-bold text-ink">家庭讨论卡</h2>
              </div>
              <div className="grid gap-3">
                {plan.family_discussion_cards.map((card) => (
                  <div key={card.topic} className="rounded-md border border-ink/10 bg-cloud p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <h3 className="font-bold text-ink">{card.topic}</h3>
                      <span className="text-xs font-bold text-clay">{card.related_rooms.join(" / ") || "全屋"}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-ink/72">{card.prompt}</p>
                    <p className="mt-2 text-xs font-bold text-tide">{card.decision_hint}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
              <div className="mb-3 flex items-center gap-2">
                <CheckCircle2 size={18} className="text-tide" aria-hidden="true" />
                <h2 className="text-lg font-bold text-ink">设计师交接问题</h2>
              </div>
              <div className="grid gap-2 text-sm leading-6 text-ink/70">
                {plan.designer_handoff_questions.map((question) => (
                  <p key={question} className="rounded-md bg-cloud px-3 py-2">{question}</p>
                ))}
              </div>
              {plan.reuse_candidates.length > 0 && (
                <div className="mt-4 rounded-md border border-ink/10 p-3">
                  <p className="text-sm font-bold text-ink">可先复用</p>
                  <div className="mt-2 grid gap-1 text-sm text-ink/68">
                    {plan.reuse_candidates.map((item) => (
                      <p key={item}>{item}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        </div>
      ) : (
        <section className="rounded-md border border-ink/10 bg-white p-5 text-sm text-ink/65 shadow-panel">
          {busy ? "正在生成生活方案包。" : "请先生成布局方案。"}
        </section>
      )}
    </PageShell>
  );
}
