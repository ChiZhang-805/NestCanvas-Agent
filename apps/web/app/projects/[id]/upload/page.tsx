"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowRight, FileImage, ImageIcon, Play, ScanLine, Upload } from "lucide-react";
import { PageShell } from "@/components/PageShell";
import {
  createStarterFloorplan,
  getJob,
  parseFloorplan,
  prepareInput,
  toAssetUrl,
  uploadAsset
} from "@/lib/api";
import { InputPreparationResult, JobStatus } from "@/lib/types";

function wait(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export default function UploadPage({ params }: { params: { id: string } }) {
  const projectId = params.id;
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploadedSignature, setUploadedSignature] = useState<string | null>(null);
  const [prepared, setPrepared] = useState<InputPreparationResult | null>(null);
  const [job, setJob] = useState<JobStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [starterBusy, setStarterBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview);
      }
    };
  }, [preview]);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    const next = event.target.files?.[0] ?? null;
    setFile(next);
    setPreview(next && next.type.startsWith("image/") ? URL.createObjectURL(next) : null);
    setUploadedSignature(null);
    setPrepared(null);
    setJob(null);
    setError(null);
  }

  function currentFileSignature() {
    return file ? `${file.name}:${file.size}:${file.lastModified}` : null;
  }

  async function ensureUploaded() {
    if (!file) {
      throw new Error("请先选择图片或 PDF。");
    }
    const signature = currentFileSignature();
    if (signature && uploadedSignature === signature) {
      return;
    }
    await uploadAsset(projectId, file);
    setUploadedSignature(signature);
  }

  async function prepareSelectedInput() {
    if (!file) return;
    setPreparing(true);
    setError(null);
    try {
      await ensureUploaded();
      setPrepared(await prepareInput(projectId));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "整理输入失败");
    } finally {
      setPreparing(false);
    }
  }

  async function uploadAndParse() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await ensureUploaded();
      setPrepared(await prepareInput(projectId));
      const created = await parseFloorplan(projectId);
      let terminalStatus: JobStatus | null = null;
      for (let attempt = 0; attempt < 30; attempt += 1) {
        const status = await getJob(created.job_id);
        setJob(status);
        if (status.status === "completed" || status.status === "failed") {
          terminalStatus = status;
          break;
        }
        await wait(1000);
      }
      if (!terminalStatus) {
        setError("解析任务仍在运行，请稍后刷新任务状态或重试。");
      }
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "上传或解析失败");
    } finally {
      setBusy(false);
    }
  }

  async function useStarterFloorplan() {
    setStarterBusy(true);
    setError(null);
    try {
      await createStarterFloorplan(projectId);
      router.push(`/projects/${projectId}/floorplan`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建草稿底图失败");
    } finally {
      setStarterBusy(false);
    }
  }

  const preparedPreview =
    prepared?.prepared_asset.mime_type.startsWith("image/")
      ? toAssetUrl(prepared.prepared_asset.local_path)
      : null;
  const canRun = Boolean(file) && !busy && !preparing && !starterBusy;

  return (
    <PageShell projectId={projectId} current="upload" title="上传户型资产">
      <div className="grid min-h-0 gap-4 xl:grid-cols-[minmax(0,1fr)_430px]">
        <section className="rounded-md border border-ink/10 bg-white p-4 shadow-panel">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-md border border-dashed border-ink/15 bg-[#f7f7f3] p-3">
              <div className="mb-3 flex items-center justify-between gap-3 text-xs font-black uppercase text-ink/55">
                原始输入
                {file && <span className="normal-case text-ink/45">{Math.round(file.size / 1024)} KB</span>}
              </div>
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={preview}
                  alt="上传预览"
                  className="h-[420px] w-full rounded-md object-contain xl:h-[520px]"
                />
              ) : (
                <div className="flex h-[420px] items-center justify-center text-ink/45 xl:h-[520px]">
                  <FileImage size={48} aria-hidden="true" />
                </div>
              )}
            </div>
            <div className="rounded-md border border-ink/10 bg-cloud p-3">
              <div className="mb-3 flex items-center justify-between gap-3 text-xs font-black uppercase text-ink/55">
                整理结果
                {prepared && <span className="normal-case text-tide">{Math.round(prepared.quality_score)} / 100</span>}
              </div>
              {preparedPreview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={preparedPreview}
                  alt="整理后的户型输入"
                  className="h-[420px] w-full rounded-md bg-white object-contain xl:h-[520px]"
                />
              ) : (
                <div className="flex h-[420px] items-center justify-center rounded-md border border-dashed border-ink/15 bg-white text-ink/45 xl:h-[520px]">
                  <ScanLine size={48} aria-hidden="true" />
                </div>
              )}
            </div>
          </div>
        </section>
        <section className="h-fit rounded-md border border-ink/10 bg-white p-5 shadow-panel">
          <label className="block text-sm font-medium text-ink" htmlFor="floorplan-upload">
            图片 / PDF / 售楼册拍照
          </label>
          <input
            id="floorplan-upload"
            type="file"
            accept="image/png,image/jpeg,image/webp,application/pdf"
            onChange={selectFile}
            className="focus-ring mt-3 w-full rounded-md border border-ink/15 px-3 py-2"
          />
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-md bg-cloud px-3 py-2 text-xs font-bold text-ink/68">手机拍摄</span>
            <span className="rounded-md bg-cloud px-3 py-2 text-xs font-bold text-ink/68">售楼册</span>
            <span className="rounded-md bg-cloud px-3 py-2 text-xs font-bold text-ink/68">截图</span>
            <span className="rounded-md bg-cloud px-3 py-2 text-xs font-bold text-ink/68">PDF</span>
          </div>
          <div className="mt-5 grid gap-2 sm:grid-cols-2">
            <button
              type="button"
              onClick={prepareSelectedInput}
              disabled={!canRun}
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink transition hover:border-ink/35 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <ScanLine size={18} aria-hidden="true" />
              {preparing ? "整理中" : "整理照片"}
            </button>
            <button
              type="button"
              onClick={uploadAndParse}
              disabled={!canRun}
              className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-tide px-4 py-2.5 font-semibold text-white transition hover:bg-moss disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? <Play size={18} aria-hidden="true" /> : <Upload size={18} aria-hidden="true" />}
              {busy ? "解析中" : "整理并解析"}
            </button>
          </div>
          <button
            type="button"
            onClick={useStarterFloorplan}
            disabled={busy || preparing || starterBusy}
            className="focus-ring mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-ink/15 bg-flax px-4 py-2.5 font-semibold text-ink transition hover:border-ink/35 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <ImageIcon size={18} aria-hidden="true" />
            {starterBusy ? "创建中" : "没有图，先用草稿底图"}
          </button>
          <Link
            href={`/projects/${projectId}/library`}
            className="focus-ring mt-3 inline-flex w-full items-center justify-center gap-2 rounded-md border border-ink/15 bg-white px-4 py-2.5 font-semibold text-ink transition hover:border-ink/35"
          >
            去户型库检索相似户型
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          {error && <p className="mt-3 text-sm text-clay">{error}</p>}
          {prepared && (
            <div className="mt-5 rounded-md bg-cloud p-4 text-sm text-ink">
              <div className="flex items-center justify-between gap-3">
                <span className="font-bold">
                  {prepared.preparation_stage === "prepared" ? "已生成整理图" : "已保留原文件"}
                </span>
                <span className="rounded-md bg-white px-2 py-1 text-xs font-black text-ink">
                  {prepared.detected_content}
                </span>
              </div>
              <div className="mt-3 h-2 rounded bg-white">
                <div
                  className="h-2 rounded bg-tide"
                  style={{ width: `${Math.max(0, Math.min(100, prepared.quality_score))}%` }}
                />
              </div>
              {prepared.operations.length > 0 && (
                <p className="mt-3 text-xs font-semibold text-ink/55">
                  {prepared.operations.join(" · ")}
                </p>
              )}
              {(prepared.warnings.length > 0 || prepared.suggestions.length > 0) && (
                <div className="mt-3 space-y-2">
                  {[...prepared.warnings, ...prepared.suggestions].slice(0, 4).map((item) => (
                    <p key={item} className="flex gap-2 text-sm text-ink/68">
                      <AlertTriangle size={15} className="mt-0.5 shrink-0 text-clay" aria-hidden="true" />
                      {item}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}
          {job && (
            <div className="mt-5 rounded-md bg-cloud p-4 text-sm text-ink">
              <div className="flex items-center justify-between gap-3">
                <span className="font-semibold">{job.stage}</span>
                <span>{job.progress}%</span>
              </div>
              <div className="mt-3 h-2 rounded bg-white">
                <div className="h-2 rounded bg-tide" style={{ width: `${job.progress}%` }} />
              </div>
              {job.status === "completed" && job.result_id && (
                <Link
                  href={`/projects/${projectId}/floorplan`}
                  className="focus-ring mt-4 inline-flex items-center gap-2 rounded-md bg-ink px-3 py-2 font-medium text-white"
                >
                  <FileImage size={16} aria-hidden="true" />
                  查看户型
                  <ArrowRight size={16} aria-hidden="true" />
                </Link>
              )}
              {job.error && <p className="mt-3 text-clay">{job.error}</p>}
            </div>
          )}
        </section>
      </div>
    </PageShell>
  );
}
