"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Database, Save, Upload } from "lucide-react";
import { FloorPlanSvg } from "@/components/FloorPlanSvg";
import { PageShell } from "@/components/PageShell";
import { getProject, patchFloorplan } from "@/lib/api";
import { FloorPlan } from "@/lib/types";

const roomTypes = [
  "living_room",
  "master_bedroom",
  "bedroom",
  "dining_room",
  "kitchen",
  "bathroom",
  "balcony",
  "storage"
];

function messageClass(message: string) {
  return message === "已保存" ? "text-tide" : "text-clay";
}

export default function FloorplanPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [floorplan, setFloorplan] = useState<FloorPlan | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getProject(projectId)
      .then((project) => {
        setFloorplan(project.floorplans.at(-1) ?? null);
      })
      .catch((caught) => {
        setMessage(caught instanceof Error ? caught.message : "加载户型失败");
      });
  }, [projectId]);

  async function save() {
    if (!floorplan?.id) return;
    setSaving(true);
    setMessage(null);
    try {
      const updated = await patchFloorplan(floorplan.id, floorplan);
      setFloorplan(updated);
      setMessage("已保存");
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "保存失败");
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageShell projectId={projectId} current="floorplan" title="校正 2D 户型">
      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <FloorPlanSvg floorplan={floorplan} />
        <section className="rounded-md border border-ink/10 bg-white p-5 shadow-panel">
          {floorplan ? (
            <>
              <label className="block text-sm font-medium text-ink" htmlFor="scale">
                比例尺 m/px
              </label>
              <input
                id="scale"
                type="number"
                step="0.001"
                min="0.001"
                value={floorplan.scale_m_per_px}
                onChange={(event) => {
                  const nextScale = event.target.valueAsNumber;
                  if (!Number.isFinite(nextScale) || nextScale <= 0) return;
                  setFloorplan({
                    ...floorplan,
                    scale_m_per_px: nextScale
                  });
                }}
                className="focus-ring mt-2 w-full rounded-md border border-ink/15 px-3 py-2"
              />
              <div className="mt-5 space-y-3">
                {floorplan.rooms.map((room, index) => (
                  <label key={room.id} className="block text-sm font-medium text-ink">
                    {room.id}
                    <select
                      value={room.room_type}
                      onChange={(event) => {
                        const rooms = [...floorplan.rooms];
                        rooms[index] = { ...room, room_type: event.target.value };
                        setFloorplan({ ...floorplan, rooms });
                      }}
                      className="focus-ring mt-1 w-full rounded-md border border-ink/15 px-3 py-2"
                    >
                      {roomTypes.map((type) => (
                        <option key={type} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              {floorplan.warnings.length > 0 && (
                <div className="mt-5 rounded-md bg-flax p-3 text-sm text-ink/75">
                  {floorplan.warnings.map((warning) => (
                    <p key={warning}>{warning}</p>
                  ))}
                </div>
              )}
              <div className="mt-5 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2 font-semibold text-white disabled:opacity-60"
                >
                  <Save size={17} aria-hidden="true" />
                  {saving ? "保存中" : "保存"}
                </button>
                <Link
                  href={`/projects/${projectId}/brief`}
                  className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2 font-semibold text-ink"
                >
                  需求
                  <ArrowRight size={17} aria-hidden="true" />
                </Link>
              </div>
              {message && <p className={`mt-3 text-sm ${messageClass(message)}`}>{message}</p>}
            </>
          ) : (
            <div className="rounded-md border border-dashed border-ink/15 bg-cloud p-5">
              {message && <p className={`mb-3 text-sm font-semibold ${messageClass(message)}`}>{message}</p>}
              <p className="text-sm font-bold text-ink">暂无可校正户型</p>
              <p className="mt-2 text-sm leading-6 text-ink/62">
                先上传图片/PDF 解析，或从户型库选一个相似模板作为起点。
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                <Link
                  href={`/projects/${projectId}/upload`}
                  className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2 font-semibold text-white"
                >
                  <Upload size={17} aria-hidden="true" />
                  上传解析
                </Link>
                <Link
                  href={`/projects/${projectId}/library`}
                  className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2 font-semibold text-ink"
                >
                  <Database size={17} aria-hidden="true" />
                  去户型库
                </Link>
              </div>
            </div>
          )}
        </section>
      </div>
    </PageShell>
  );
}
