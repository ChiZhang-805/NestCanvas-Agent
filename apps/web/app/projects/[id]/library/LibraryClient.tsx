"use client";

import Link from "next/link";
import { FormEvent, useMemo, useState } from "react";
import { ArrowRight, CheckCircle2, Database, ExternalLink, Filter, Search } from "lucide-react";
import { FloorPlanSvg } from "@/components/FloorPlanSvg";
import { backendAssetUrl, createLibraryFloorplan, searchFloorplanLibrary } from "@/lib/api";
import { FloorPlanDatasetSource, FloorPlanLibraryItem } from "@/lib/types";

const bedroomOptions = [
  { label: "不限", value: "" },
  { label: "开间", value: "0" },
  { label: "一居", value: "1" },
  { label: "两居", value: "2" },
  { label: "三居", value: "3" },
  { label: "四居", value: "4" }
];

const quickTags = ["一家三口", "高收纳", "采光", "老人房", "居家办公", "二孩家庭"];

function optionalPositiveNumber(value: string): number | undefined {
  if (value.trim() === "") return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : undefined;
}

function commercialLabel(value: FloorPlanDatasetSource["commercial_use"]) {
  if (value === "allowed") return "开放源";
  if (value === "restricted") return "研究源";
  return "待核验";
}

function licenseTone(value: FloorPlanDatasetSource["commercial_use"]) {
  if (value === "allowed") return "bg-moss/12 text-moss";
  if (value === "restricted") return "bg-clay/12 text-clay";
  return "bg-ink/8 text-ink/62";
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

  const sourceById = useMemo(() => new Map(sources.map((source) => [source.id, source])), [sources]);

  async function load(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      const response = await searchFloorplanLibrary({
        query,
        bedrooms: optionalPositiveNumber(bedrooms),
        minArea: optionalPositiveNumber(minArea),
        maxArea: optionalPositiveNumber(maxArea),
        dataset: dataset || undefined,
        limit: 100
      });
      setItems(response.items);
      setSources(response.sources);
      setSelectedId(response.items[0]?.id ?? null);
      if (!response.items.length) {
        setMessage("没有匹配户型。可以放宽面积、卧室数或关键词。");
      }
    } catch (caught) {
      setMessage(caught instanceof Error ? caught.message : "户型库加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function chooseTemplate(template: FloorPlanLibraryItem) {
    setBusyId(template.id);
    setSelectedId(template.id);
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

  return (
    <div className="space-y-5">
      <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold uppercase text-clay">
              <Filter size={15} aria-hidden="true" />
              Retrieval filters
            </div>
            <p className="mt-2 text-sm leading-6 text-ink/62">
              上方筛选，下方显示完整户型卡片。现在返回结构化种子样本，外部数据导入后会显示真实图片或数据缩略图。
            </p>
          </div>
          <Link
            href={`/projects/${projectId}/floorplan`}
            className="focus-ring inline-flex min-h-10 items-center gap-2 rounded-md border border-ink/15 bg-white px-3 py-2 text-sm font-bold text-ink transition hover:border-ink/35"
          >
            去校正页
            <ArrowRight size={15} aria-hidden="true" />
          </Link>
        </div>

        <form onSubmit={load} className="mt-4 grid gap-3 xl:grid-cols-[1.45fr_0.7fr_0.65fr_0.65fr_0.9fr_auto]">
          <label className="min-w-0 text-sm font-bold text-ink" htmlFor="library-query">
            需求关键词
            <input
              id="library-query"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="一家三口、老人房、高收纳、采光..."
              className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3 font-semibold"
            />
          </label>
          <label className="min-w-0 text-sm font-bold text-ink">
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
          <label className="min-w-0 text-sm font-bold text-ink">
            最小面积
            <input
              value={minArea}
              onChange={(event) => setMinArea(event.target.value)}
              type="number"
              min="0"
              placeholder="m2"
              className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
            />
          </label>
          <label className="min-w-0 text-sm font-bold text-ink">
            最大面积
            <input
              value={maxArea}
              onChange={(event) => setMaxArea(event.target.value)}
              type="number"
              min="0"
              placeholder="m2"
              className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
            />
          </label>
          <label className="min-w-0 text-sm font-bold text-ink">
            数据源
            <select
              value={dataset}
              onChange={(event) => setDataset(event.target.value)}
              className="focus-ring mt-2 min-h-11 w-full rounded-md border border-ink/15 px-3"
            >
              <option value="">全部来源</option>
              {sources.map((source) => (
                <option key={source.id} value={source.id}>
                  {source.name}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={loading}
            className="focus-ring mt-0 inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 font-bold text-white transition hover:bg-tide disabled:opacity-60 xl:mt-7"
          >
            <Search size={17} aria-hidden="true" />
            {loading ? "检索中" : "检索"}
          </button>
        </form>

        <div className="mt-4 flex flex-wrap gap-2">
          {quickTags.map((tag) => (
            <button
              key={tag}
              type="button"
              onClick={() => setQuery((current) => (current.includes(tag) ? current : `${current} ${tag}`.trim()))}
              className="focus-ring rounded-md border border-ink/10 bg-cloud px-3 py-1.5 text-xs font-bold text-ink/70 transition hover:border-ink/30"
            >
              {tag}
            </button>
          ))}
        </div>

        {message && (
          <p className="mt-4 rounded-md border border-tide/20 bg-tide/8 px-3 py-2 text-sm font-semibold text-tide">
            {message}
          </p>
        )}
      </section>

      <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-bold text-ink">
            <Database size={16} aria-hidden="true" />
            数据源状态
          </div>
          <p className="text-xs font-semibold text-ink/55">
            当前 {items.length} 个可检索样本，真实数据子集可按同一 schema 挂入。
          </p>
        </div>
        <div className="mt-3 grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {sources.map((source) => (
            <a
              key={source.id}
              href={source.url.startsWith("http") ? source.url : undefined}
              target="_blank"
              rel="noreferrer"
              className="focus-ring min-w-0 rounded-md border border-ink/10 p-3 transition hover:border-ink/35"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-bold text-ink">{source.name}</span>
                <span className={`shrink-0 rounded-md px-2 py-1 text-[11px] font-black ${licenseTone(source.commercial_use)}`}>
                  {commercialLabel(source.commercial_use)}
                </span>
              </div>
              <p className="mt-2 line-clamp-2 text-xs leading-5 text-ink/58">{source.license}</p>
              {source.url.startsWith("http") && (
                <span className="mt-2 inline-flex items-center gap-1 text-xs font-bold text-tide">
                  来源
                  <ExternalLink size={12} aria-hidden="true" />
                </span>
              )}
            </a>
          ))}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => {
          const source = sourceById.get(item.source_dataset_id);
          const selected = selectedId === item.id;
          return (
            <article
              key={item.id}
              className={`min-w-0 rounded-md border bg-white shadow-panel transition ${
                selected ? "border-tide ring-2 ring-tide/15" : "border-ink/10 hover:border-ink/30"
              }`}
            >
              <button
                type="button"
                onClick={() => setSelectedId(item.id)}
                className="focus-ring block w-full rounded-t-md p-3 text-left"
                title={`查看 ${item.title}`}
              >
                <div className="aspect-[4/3] overflow-hidden rounded-md bg-cloud">
                  {item.preview_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={backendAssetUrl(item.preview_image_url) ?? ""} alt={item.title} className="h-full w-full object-cover" />
                  ) : (
                    <div className="h-full w-full p-2">
                      <FloorPlanSvg floorplan={item.floorplan} compact />
                    </div>
                  )}
                </div>
                <div className="mt-3 flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-xs font-black uppercase text-clay">{item.source_dataset_name}</p>
                    <h2 className="mt-1 line-clamp-2 min-h-12 text-lg font-bold leading-6 text-ink">{item.title}</h2>
                  </div>
                  <span className="shrink-0 rounded-md bg-ink px-2 py-1 text-xs font-black text-white">
                    {Math.round(item.match_score)}
                  </span>
                </div>
              </button>

              <div className="px-3 pb-3">
                <div className="grid grid-cols-3 gap-2 text-center text-xs font-bold text-ink/72">
                  <span className="rounded-md bg-cloud px-2 py-2">{item.area_m2} m2</span>
                  <span className="rounded-md bg-cloud px-2 py-2">{item.bedrooms} 室</span>
                  <span className="rounded-md bg-cloud px-2 py-2">{item.bathrooms} 卫</span>
                </div>

                <p className="mt-3 line-clamp-1 text-xs font-semibold text-ink/58">
                  {item.household_fit.join(" / ")}
                </p>
                <div className="mt-2 flex min-h-16 flex-wrap content-start gap-1.5">
                  {item.tags.slice(0, 6).map((tag) => (
                    <span key={tag} className="rounded bg-tide/8 px-2 py-1 text-[11px] font-bold text-tide">
                      {tag}
                    </span>
                  ))}
                </div>

                <div className="mt-3 flex items-center justify-between gap-3 border-t border-ink/10 pt-3">
                  <span
                    className={`min-w-0 truncate rounded-md px-2 py-1 text-[11px] font-black ${
                      licenseTone(item.commercial_use)
                    }`}
                    title={item.license}
                  >
                    {source ? commercialLabel(source.commercial_use) : commercialLabel(item.commercial_use)}
                  </span>
                  <button
                    type="button"
                    onClick={() => chooseTemplate(item)}
                    disabled={busyId !== null}
                    className="focus-ring inline-flex min-h-10 shrink-0 items-center gap-2 rounded-md bg-tide px-3 py-2 text-sm font-bold text-white transition hover:bg-moss disabled:opacity-60"
                  >
                    {busyId === item.id ? "写入中" : "选用"}
                    {selected ? <CheckCircle2 size={15} aria-hidden="true" /> : <ArrowRight size={15} aria-hidden="true" />}
                  </button>
                </div>
              </div>
            </article>
          );
        })}
      </section>

      {!items.length && (
        <section className="rounded-md border border-dashed border-ink/20 bg-white p-8 text-center text-sm font-semibold text-ink/58">
          暂无匹配模板。
        </section>
      )}
    </div>
  );
}
