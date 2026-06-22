"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Download, ImageIcon, WandSparkles } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import { exportProject, getProject, renderOption, toAssetUrl } from "@/lib/api";
import { LayoutOption, ProjectDetail, RenderAsset } from "@/lib/types";

const disclaimer = "概念效果图仅用于灵感展示，尺寸和可施工性以平面图校正结果为准。";

export default function RendersPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [busyOption, setBusyOption] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportUrl, setExportUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isCurrent = true;

    async function loadProject() {
      setError(null);
      setProject(null);
      const loaded = await getProject(projectId);
      if (isCurrent) {
        setProject(loaded);
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

  async function render(option: LayoutOption) {
    setBusyOption(option.id);
    setError(null);
    try {
      const asset = await renderOption(option.id);
      setProject((current) =>
        current
          ? {
              ...current,
              renders: [...current.renders, asset]
            }
          : current
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "渲染失败");
    } finally {
      setBusyOption(null);
    }
  }

  async function exportCurrentProject() {
    setExporting(true);
    setError(null);
    try {
      const asset = await exportProject(projectId);
      const url = toAssetUrl(asset.local_path);
      setExportUrl(url);
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "导出失败");
    } finally {
      setExporting(false);
    }
  }

  const options = project?.layout_options ?? [];
  const renders: RenderAsset[] = project?.renders ?? [];

  return (
    <PageShell projectId={projectId} current="renders" title="概念效果图">
      <div className="mb-5 rounded-md border border-clay/30 bg-white p-4 text-sm font-medium text-ink shadow-panel">
        {disclaimer}
      </div>
      <div className="mb-6 flex flex-wrap gap-3">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => render(option)}
            disabled={busyOption !== null}
            className="focus-ring inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white disabled:opacity-60"
          >
            <WandSparkles size={17} aria-hidden="true" />
            {busyOption === option.id ? "生成中" : option.strategy}
          </button>
        ))}
        <button
          type="button"
          onClick={exportCurrentProject}
          disabled={exporting}
          className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink transition hover:border-ink/35 disabled:opacity-60"
        >
          <Download size={17} aria-hidden="true" />
          {exporting ? "导出中" : "导出项目 JSON"}
        </button>
        {exportUrl && (
          <a
            href={exportUrl}
            target="_blank"
            rel="noreferrer"
            className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-tide"
          >
            下载最近导出
          </a>
        )}
        {error && <span className="text-sm text-clay">{error}</span>}
      </div>
      <div className="grid gap-5 md:grid-cols-2">
        {renders.map((renderAsset) => (
          <section key={renderAsset.id} className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={toAssetUrl(renderAsset.output_path)}
              alt="概念效果图"
              className="aspect-[3/2] w-full rounded-md object-cover"
            />
            <p className="mt-3 text-sm font-medium text-ink">{renderAsset.disclaimer}</p>
            <details className="mt-3 rounded-md bg-cloud p-3 text-sm text-ink/70">
              <summary className="cursor-pointer font-bold text-ink">渲染 prompt</summary>
              <p className="mt-2 leading-6">{renderAsset.prompt}</p>
            </details>
          </section>
        ))}
        {renders.length === 0 && (
          <section className="flex aspect-[3/2] items-center justify-center rounded-md border border-dashed border-ink/20 bg-white p-5 text-center text-ink/60">
            <div>
              <ImageIcon size={40} className="mx-auto" aria-hidden="true" />
              <p className="mt-3 text-sm font-bold text-ink">
                {options.length ? "选择上方方案生成概念图" : "还没有可渲染的布局方案"}
              </p>
              {!options.length && (
                <Link
                  href={`/projects/${projectId}/options`}
                  className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md bg-tide px-4 py-2 font-semibold text-white"
                >
                  生成布局方案
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              )}
            </div>
          </section>
        )}
      </div>
    </PageShell>
  );
}
