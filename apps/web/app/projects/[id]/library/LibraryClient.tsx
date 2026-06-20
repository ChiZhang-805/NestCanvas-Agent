"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowRight, Database, Filter, Search } from "lucide-react";
import { FloorPlanSvg } from "@/components/FloorPlanSvg";
import { createLibraryFloorplan, searchFloorplanLibrary } from "@/lib/api";
import { FloorPlanDatasetSource, FloorPlanLibraryItem } from "@/lib/types";

const bedroomOptions = [
  { label: "不限", value: "" },
  { label: "开间", value: "0" },
  { label: "一居", value: "1" },
  { label: "两居", value: "2" },
  { label: "三居", value: "3" },
  { label: "四居", value: "4" }
];

function optionalPositiveNumber(value: string): number | undefined {
  if (value.trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

export function LibraryClient({
  projectId,
  initialItems,
  initialSources,
  initialMessage
}: {
  projectId: string;
  initialItems: FloorPlanLibraryItem[];
  initialSources: FloorPlanDatasetSource[];
  initialMessage?: string | null;
}) {
  const [query, setQuery] = useState("一家三口 收纳");
  const [bedrooms, setBedrooms] = useState("2");
  const [minArea, setMinArea] = useState("");
  const [maxArea, setMaxArea] = useState("");
  const [dataset, setDataset] = useState("");
  const [items, setItems] = useState<FloorPlanLibraryItem[]>(initialItems);
  const [sources, setSources] = useState<FloorPlanDatasetSource[]>(initialSources);
  const [selectedId, setSelectedId] = useState<string | null>(initialItems[0]?.id ?? null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(initialMessage ?? null);

  async function load() {
    setLoading(true);
    setMessage(null);
    try {
      const response = await searchFloorplanLibrary({
        query,
        bedrooms: optionalPositiveNumber(bedrooms),
        minArea: optionalPositiveNumber(minArea),
        maxArea: optionalPositiveNumber(maxArea),
        dataset: dataset || undefined,
        limit: 12
      });
      setItems(response.items);
      setSources(response.sources);
      setSelectedId(response.items[0]?.id ?? null);
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "户型库加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function chooseTemplate(template: FloorPlanLibraryItem) {
    setBusyId(template.id);
    setMessage(null);
    try {
      await createLibraryFloorplan(projectId, template.id);
      setMessage(`已选用：${template.title}`);
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "选用模板失败");
    } finally {
      setBusyId(null);
    }
  }

  const selected = items.find((item) => item.id === selectedId) ?? items[0] ?? null;

  return (
    <div className="grid gap-5 lg:grid-cols-[0.82fr_1.18fr]">
      <section className="space-y-4">
        <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2 text-xs font-bold uppercase text-clay">
            <Filter size={15} aria-hidden="true" />
            Retrieval filters
          </div>
          <label className="mt-4 block text-sm font-bold text-ink" htmlFor="library-query">
            需求关键词
          </label>
          <input
            id="library-query"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="一家三口、老人房、高收纳、采光..."
            className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3 font-semibold"
          />

          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <label className="text-sm font-bold text-ink">
              卧室数
              <select
                value={bedrooms}
                onChange={(event) => setBedrooms(event.target.value)}
                className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
              >
                {bedroomOptions.map((option) => (
                  <option key={option.label} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold text-ink">
              最小面积
              <input
                value={minArea}
                onChange={(event) => setMinArea(event.target.value)}
                type="number"
                min="0"
                className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
              />
            </label>
            <label className="text-sm font-bold text-ink">
              最大面积
              <input
                value={maxArea}
                onChange={(event) => setMaxArea(event.target.value)}
                type="number"
                min="0"
                className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
              />
            </label>
          </div>

          <label className="mt-3 block text-sm font-bold text-ink">
            数据源
            <select
              value={dataset}
              onChange={(event) => setDataset(event.target.value)}
              className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
            >
              <option value="">全部可用模板</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="focus-ring mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 font-bold text-white transition hover:bg-tide disabled:opacity-60"
          >
            <Search size={17} aria-hidden="true" />
            {loading ? "检索中" : "检索户型"}
          </button>
          {message && <p className="mt-3 text-sm font-semibold text-tide">{message}</p>}
        </div>

        <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
          <div className="flex items-center gap-2 text-sm font-bold text-ink">
            <Database size={16} aria-hidden="true" />
            可接入数据源
          </div>
          <div className="mt-3 space-y-3">
            {sources.map((source) => (
              <a
                key={source.id}
                href={source.url.startsWith("http") ? source.url : undefined}
                target="_blank"
                rel="noreferrer"
                className="block rounded-md border border-ink/10 p-3 transition hover:border-ink/35"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-bold text-ink">{source.name}</span>
                  <span className="rounded-md bg-cloud px-2 py-1 text-xs font-black text-ink/62">
                    {source.commercial_use}
                  </span>
                </div>
                <p className="mt-2 text-xs leading-5 text-ink/58">{source.license}</p>
              </a>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.88fr_1.12fr]">
        <div className="space-y-3">
          {items.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setSelectedId(item.id)}
              className={`focus-ring w-full rounded-md border p-4 text-left shadow-panel transition ${
                selected?.id === item.id
                  ? "border-ink bg-ink text-white"
                  : "border-ink/10 bg-white text-ink hover:border-ink/35"
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase opacity-70">{item.source_dataset_name}</p>
                  <h2 className="mt-1 font-bold">{item.title}</h2>
                </div>
                <span className="rounded-md bg-white/14 px-2 py-1 text-xs font-black">
                  {Math.round(item.match_score)}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-3 gap-2 text-xs font-bold opacity-78">
                <span>{item.area_m2} m2</span>
                <span>{item.bedrooms} 室</span>
                <span>{item.bathrooms} 卫</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {item.tags.slice(0, 4).map((tag) => (
                  <span key={tag} className="rounded bg-white/14 px-2 py-1 text-[11px] font-bold">
                    {tag}
                  </span>
                ))}
              </div>
            </button>
          ))}
        </div>

        <div className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-black uppercase text-clay">Selected template</p>
                  <h2 className="mt-1 text-xl font-bold text-ink">{selected.title}</h2>
                  <p className="mt-2 text-sm font-semibold text-ink/62">
                    {selected.household_fit.join(" / ")}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => chooseTemplate(selected)}
                  disabled={busyId !== null}
                  className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-bold text-white transition hover:bg-moss disabled:opacity-60"
                >
                  {busyId === selected.id ? "写入中" : "选用此户型"}
                  <ArrowRight size={16} aria-hidden="true" />
                </button>
              </div>
              <div className="mt-4">
                <FloorPlanSvg floorplan={selected.floorplan} />
              </div>
              <div className="mt-4 rounded-md bg-cloud p-3 text-sm leading-6 text-ink/68">
                <p className="font-bold text-ink">来源与许可</p>
                <p>{selected.source_dataset_name} · {selected.license}</p>
                <p>当前模板是结构化种子样本；真实数据集接入后，会沿用同一套检索字段。</p>
              </div>
              <Link
                href={`/projects/${projectId}/floorplan`}
                className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-bold text-ink transition hover:border-ink/35"
              >
                去校正页
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            </>
          ) : (
            <p className="text-sm text-ink/60">暂无匹配模板。</p>
          )}
        </div>
      </section>
    </div>
  );
}
