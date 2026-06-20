"use client";

import { AlertTriangle, CheckCircle2, ClipboardList, RefreshCw, Sparkles } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { PageShell } from "@/components/PageShell";
import { createHomeCoach, getProjectWorkflow } from "@/lib/api";
import type { HomeCoachPackage, ProjectWorkflow, WorkflowStep } from "@/lib/types";

function statusClass(status: WorkflowStep["status"]) {
  if (status === "done") return "border-tide/25 bg-tide/5 text-tide";
  if (status === "available") return "border-flax bg-flax text-ink";
  if (status === "blocked") return "border-clay/25 bg-clay/5 text-clay";
  return "border-ink bg-ink text-white";
}

function statusLabel(status: WorkflowStep["status"]) {
  if (status === "done") return "完成";
  if (status === "available") return "可执行";
  if (status === "blocked") return "阻断";
  return "当前";
}

export default function CoachPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [workflow, setWorkflow] = useState<ProjectWorkflow | null>(null);
  const [coach, setCoach] = useState<HomeCoachPackage | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setBusy(true);
    setMessage(null);
    try {
      const nextWorkflow = await getProjectWorkflow(projectId);
      setWorkflow(nextWorkflow);
      try {
        setCoach(await createHomeCoach(projectId));
      } catch (caught) {
        setCoach(null);
        setMessage(caught instanceof Error ? caught.message : "Home Coach 暂不可生成");
      }
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "工作流加载失败");
    } finally {
      setBusy(false);
    }
  }, [projectId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <PageShell projectId={projectId} current="coach" title="Home Coach 工作流">
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={load}
          disabled={busy}
          className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white disabled:opacity-60"
        >
          <RefreshCw size={17} aria-hidden="true" />
          {busy ? "刷新中" : "刷新助手"}
        </button>
        {message && <span className="text-sm text-clay">{message}</span>}
      </div>

      {workflow ? (
        <div className="grid gap-5">
          <section className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <p className="text-xs font-bold uppercase text-clay">Workflow control</p>
                <h2 className="mt-1 text-xl font-bold text-ink">当前步骤：{workflow.current_step}</h2>
                <p className="mt-3 text-sm leading-6 text-ink/70">{workflow.summary}</p>
              </div>
              <div className="rounded-md bg-ink px-4 py-3 text-right text-white">
                <p className="text-xs font-bold uppercase opacity-70">准备度</p>
                <p className="mt-1 text-2xl font-black">{workflow.readiness_score}</p>
              </div>
            </div>
          </section>

          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            {workflow.steps.map((step) => (
              <div key={step.key} className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-bold text-ink">{step.label}</h3>
                  <span className={`rounded-md border px-2 py-1 text-xs font-black ${statusClass(step.status)}`}>
                    {statusLabel(step.status)}
                  </span>
                </div>
                <p className="mt-2 text-xs font-bold text-ink/45">{step.artifact_count} artifacts</p>
                <p className="mt-3 text-sm leading-6 text-ink/68">{step.automation_hint}</p>
                {[...step.blockers, ...step.next_actions].slice(0, 3).map((item) => (
                  <p key={item} className="mt-2 flex gap-2 text-xs leading-5 text-ink/60">
                    {step.blockers.includes(item) ? (
                      <AlertTriangle size={14} className="mt-0.5 shrink-0 text-clay" aria-hidden="true" />
                    ) : (
                      <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-tide" aria-hidden="true" />
                    )}
                    {item}
                  </p>
                ))}
              </div>
            ))}
          </section>

          {coach && (
            <>
              <section className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
                <div className="mb-3 flex items-center gap-2">
                  <Sparkles size={18} className="text-tide" aria-hidden="true" />
                  <h2 className="text-lg font-bold text-ink">Home Coach 包</h2>
                </div>
                <p className="text-sm leading-6 text-ink/70">{coach.summary}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2">
                  {coach.family_script.slice(0, 4).map((item) => (
                    <p key={item} className="rounded-md bg-cloud px-3 py-2 text-sm leading-6 text-ink/70">{item}</p>
                  ))}
                </div>
              </section>

              <section className="grid gap-4 lg:grid-cols-2">
                {coach.room_cards.map((card) => (
                  <div key={card.room_id} className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
                    <p className="text-xs font-black uppercase text-clay">{card.room_type}</p>
                    <h3 className="mt-1 font-bold text-ink">{card.headline}</h3>
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {card.current_furniture.slice(0, 6).map((item) => (
                        <span key={item} className="rounded-md bg-cloud px-2 py-1 text-xs font-bold text-ink/68">{item}</span>
                      ))}
                    </div>
                    <div className="mt-3 grid gap-2 text-sm leading-6 text-ink/68">
                      {card.daily_use_notes.map((item) => <p key={item}>{item}</p>)}
                    </div>
                    {card.shopping_focus.length > 0 && (
                      <div className="mt-3 rounded-md bg-flax p-3 text-xs leading-5 text-ink/70">
                        {card.shopping_focus.map((item) => <p key={item}>{item}</p>)}
                      </div>
                    )}
                    <details className="mt-3 rounded-md border border-ink/10 p-3 text-xs text-ink/62">
                      <summary className="cursor-pointer font-bold text-ink">量尺任务与视觉提示</summary>
                      <div className="mt-2 grid gap-1">
                        {card.measurement_tasks.map((item) => <p key={item}>{item}</p>)}
                      </div>
                      <p className="mt-2 font-semibold text-tide">{card.visual_prompt}</p>
                    </details>
                  </div>
                ))}
              </section>
            </>
          )}

          <section className="grid gap-5 lg:grid-cols-2">
            <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
              <div className="mb-3 flex items-center gap-2">
                <Sparkles size={18} className="text-tide" aria-hidden="true" />
                <h2 className="text-lg font-bold text-ink">可接入大模型模块</h2>
              </div>
              <div className="grid gap-2">
                {(coach?.llm_upgrade_plan ?? workflow.llm_modules).map((item) => (
                  <p key={item.key} className="rounded-md bg-cloud px-3 py-2 text-sm leading-6 text-ink/70">
                    <span className="font-bold text-ink">{item.label}</span> · {item.purpose}
                  </p>
                ))}
              </div>
            </div>
            <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
              <div className="mb-3 flex items-center gap-2">
                <ClipboardList size={18} className="text-tide" aria-hidden="true" />
                <h2 className="text-lg font-bold text-ink">便携式服务</h2>
              </div>
              <div className="grid gap-2">
                {(coach?.portable_services ?? workflow.portable_services).map((item) => (
                  <p key={item.key} className="rounded-md bg-cloud px-3 py-2 text-sm leading-6 text-ink/70">
                    <span className="font-bold text-ink">{item.label}</span> · {item.service_type} · {item.status}
                  </p>
                ))}
              </div>
            </div>
          </section>
        </div>
      ) : (
        <section className="rounded-md border border-ink/10 bg-white p-5 text-sm text-ink/65 shadow-panel">
          {busy ? "正在加载工作流。" : "暂无工作流数据。"}
        </section>
      )}
    </PageShell>
  );
}
