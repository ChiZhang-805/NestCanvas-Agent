"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Download,
  FolderOpen,
  ImageIcon,
  Menu,
  MessageSquareText,
  Ruler,
  Sofa,
  Upload,
  WandSparkles
} from "lucide-react";
import { BeforeAfterHero, HeroMode } from "@/components/BeforeAfterHero";
import { OpenAIKeyPanel } from "@/components/OpenAIKeyPanel";
import { createDemoProject, createProject } from "@/lib/api";
import { useProjectStore } from "@/store/projectStore";

type ActionTarget = "upload" | "floorplan" | "brief" | "options" | "renders";
type ActionMode = "new" | "demo";
type DemoTarget = Exclude<ActionTarget, "upload">;

const workflow = [
  { key: "upload", label: "上传", icon: Upload },
  { key: "floorplan", label: "校正", icon: Ruler },
  { key: "brief", label: "需求", icon: MessageSquareText },
  { key: "options", label: "方案", icon: Sofa },
  { key: "renders", label: "渲染", icon: ImageIcon }
] as const;

const quickActions: Array<{
  label: string;
  description: string;
  icon: typeof Upload;
  target: ActionTarget;
  mode: ActionMode;
}> = [
  {
    label: "上传资产",
    description: "新建项目",
    icon: Upload,
    target: "upload",
    mode: "new"
  },
  {
    label: "校正户型",
    description: "示例画布",
    icon: Ruler,
    target: "floorplan",
    mode: "demo"
  },
  {
    label: "填写需求",
    description: "结构化 brief",
    icon: MessageSquareText,
    target: "brief",
    mode: "demo"
  },
  {
    label: "生成方案",
    description: "多方案比较",
    icon: Sofa,
    target: "options",
    mode: "demo"
  },
  {
    label: "查看渲染",
    description: "概念效果",
    icon: WandSparkles,
    target: "renders",
    mode: "demo"
  },
  {
    label: "导出分享",
    description: "方案交付",
    icon: Download,
    target: "renders",
    mode: "demo"
  }
];

const modeCopy: Record<
  HeroMode,
  {
    eyebrow: string;
    title: string;
    body: string;
    cta: string;
    target: ActionTarget;
    mode: ActionMode;
    progress: string;
  }
> = {
  upload: {
    eyebrow: "Home design canvas",
    title: "NestCanvas\nAgent 栖画",
    body: "从一张空房照片或户型图开始，串联空间识别、需求整理和方案比较。\n把概念渲染沉淀成可落地的家居创作流程。",
    cta: "开始创作",
    target: "upload",
    mode: "new",
    progress: "1 / 5"
  },
  floorplan: {
    eyebrow: "Geometry calibration",
    title: "校正空间尺度",
    body: "校准墙体、门窗、房间和比例，形成可靠底图。\n后续家具坐标和动线判断，都以这里为准。",
    cta: "进入校正",
    target: "floorplan",
    mode: "demo",
    progress: "2 / 5"
  },
  brief: {
    eyebrow: "Lifestyle brief",
    title: "表达生活方式",
    body: "沉淀风格、预算、收纳、成员和偏好禁忌。\n让生成结果更接近真实居住需求。",
    cta: "填写需求",
    target: "brief",
    mode: "demo",
    progress: "3 / 5"
  },
  options: {
    eyebrow: "Layout options",
    title: "比较多套布局",
    body: "生成多套家具方案，同屏检查碰撞、挡门和通道。\n把面积利用和可选项变得清楚。",
    cta: "查看方案",
    target: "options",
    mode: "demo",
    progress: "4 / 5"
  },
  renders: {
    eyebrow: "Concept render",
    title: "渲染理想居所",
    body: "生成概念效果图，快速沟通氛围、材质和软装。\n尺寸和可施工性仍回到平面图校验。",
    cta: "查看渲染",
    target: "renders",
    mode: "demo",
    progress: "5 / 5"
  }
};

export default function HomePage() {
  const [title, setTitle] = useState("我的栖画项目");
  const [activeMode, setActiveMode] = useState<HeroMode>("upload");
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState<DemoTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const setCurrentProjectId = useProjectStore((state) => state.setCurrentProjectId);
  const activeCopy = modeCopy[activeMode];
  const isNavigating = busy || actionBusy !== null;

  async function createUploadProject() {
    if (isNavigating) return;
    setBusy(true);
    setError(null);
    try {
      const project = await createProject(title.trim() || "未命名栖画项目");
      setCurrentProjectId(project.id);
      router.push(`/projects/${project.id}/upload`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "创建项目失败");
    } finally {
      setBusy(false);
    }
  }

  async function openDemo(target: DemoTarget) {
    if (isNavigating) return;
    setActionBusy(target);
    setError(null);
    try {
      const project = await createDemoProject();
      setCurrentProjectId(project.id);
      router.push(`/projects/${project.id}/${target}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "示例项目创建失败");
    } finally {
      setActionBusy(null);
    }
  }

  async function runAction(target: ActionTarget, mode: ActionMode) {
    if (mode === "new") {
      await createUploadProject();
      return;
    }
    await openDemo(target === "upload" ? "options" : target);
  }

  return (
    <main className="h-[100svh] overflow-hidden bg-cloud text-ink">
      <section className="relative h-full overflow-hidden">
        <BeforeAfterHero className="absolute inset-0 rounded-none" mode={activeMode} />

        <header className="relative z-30 mx-auto flex max-w-[1800px] items-center justify-between gap-4 px-5 py-5 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-md border border-ink/25 bg-white/64 shadow-panel backdrop-blur">
              <WandSparkles size={20} aria-hidden="true" />
            </div>
            <div className="text-sm font-bold leading-none">
              NestCanvas
              <br />
              Agent 栖画
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded-md border border-ink/25 bg-white/64 px-4 py-2 text-xs font-bold uppercase backdrop-blur sm:inline-flex">
              Local Engine
            </span>
            <button
              type="button"
              onClick={() => openDemo("options")}
              disabled={isNavigating}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/25 bg-white/64 px-3 py-2 text-xs font-bold uppercase backdrop-blur transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <FolderOpen size={15} aria-hidden="true" />
              项目
            </button>
            <button
              type="button"
              onClick={() => openDemo("brief")}
              disabled={isNavigating}
              className="focus-ring inline-flex items-center gap-2 rounded-md border border-ink/25 bg-white/64 px-3 py-2 text-xs font-bold uppercase backdrop-blur transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Menu size={15} aria-hidden="true" />
              菜单
            </button>
          </div>
        </header>

        <aside className="absolute left-6 top-1/2 z-30 hidden -translate-y-1/2 space-y-3 xl:block">
          {workflow.map((item) => {
            const Icon = item.icon;
            const selected = activeMode === item.key;
            return (
              <button
                key={item.key}
                type="button"
                aria-pressed={selected}
                onClick={() => setActiveMode(item.key)}
                className={`focus-ring flex min-w-28 items-center gap-3 rounded-md border px-3 py-2 text-sm font-bold backdrop-blur transition ${
                  selected
                    ? "border-ink bg-ink text-white shadow-panel"
                    : "border-white/50 bg-white/52 text-ink/78 hover:bg-white hover:text-ink"
                }`}
              >
                <Icon size={16} aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </aside>

        <div className="absolute bottom-5 left-4 right-4 z-30 grid grid-cols-5 gap-2 xl:hidden">
          {workflow.map((item) => {
            const Icon = item.icon;
            const selected = activeMode === item.key;
            return (
              <button
                key={item.key}
                type="button"
                aria-pressed={selected}
                onClick={() => setActiveMode(item.key)}
                className={`focus-ring flex min-h-14 flex-col items-center justify-center gap-1 rounded-md border text-xs font-bold backdrop-blur transition ${
                  selected
                    ? "border-ink bg-ink text-white"
                    : "border-white/50 bg-white/62 text-ink/78"
                }`}
              >
                <Icon size={15} aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </div>

        <div
          className="absolute max-w-[760px]"
          style={{
            left: "clamp(180px, 16vw, 340px)",
            top: "46%",
            transform: "translateY(-50%)",
            zIndex: 60
          }}
        >
          <div
            className="pointer-events-none absolute rounded-md bg-white/38 blur-xl"
            style={{
              inset: "-32px -44px -28px -44px"
            }}
            aria-hidden="true"
          />
          <div className="relative">
            <p className="text-sm font-black uppercase tracking-normal text-tide drop-shadow-[0_2px_14px_rgba(255,255,255,0.95)]">
              {activeCopy.eyebrow}
            </p>
            <h1
              className={`mt-4 whitespace-pre-line font-black leading-[0.94] text-ink drop-shadow-[0_3px_20px_rgba(255,255,255,0.96)] ${
                activeMode === "upload"
                  ? "max-w-3xl text-5xl sm:text-7xl xl:text-8xl"
                  : "max-w-[900px] text-5xl sm:text-7xl xl:text-[6.8rem]"
              }`}
            >
              {activeCopy.title}
            </h1>
            <p className="mt-5 max-w-[650px] whitespace-pre-line text-base font-bold leading-7 text-ink/78 drop-shadow-[0_2px_14px_rgba(255,255,255,0.95)] sm:text-lg">
              {activeCopy.body}
            </p>
            <div className="mt-8">
              <button
                type="button"
                onClick={() => runAction(activeCopy.target, activeCopy.mode)}
                disabled={isNavigating}
                className="focus-ring inline-flex min-h-14 min-w-44 items-center justify-center gap-3 rounded-md border border-ink/45 bg-ink px-6 font-black text-white shadow-[0_18px_45px_rgba(34,49,44,0.22)] backdrop-blur transition hover:bg-tide disabled:cursor-not-allowed disabled:opacity-60"
              >
                <WandSparkles size={18} aria-hidden="true" />
                {isNavigating ? "准备中" : activeCopy.cta}
                <ArrowRight size={17} aria-hidden="true" />
              </button>
            </div>
            {error && <p className="mt-3 text-sm font-medium text-clay">{error}</p>}
          </div>
        </div>

        <section className="absolute right-8 top-1/2 z-30 hidden w-[380px] -translate-y-1/2 rounded-md border border-white/40 bg-white/66 p-5 text-ink shadow-panel backdrop-blur-xl xl:block">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-bold uppercase text-clay">MVP controls</p>
              <h2 className="mt-1 text-xl font-bold">快速入口</h2>
            </div>
            <span className="rounded-md border border-ink/20 px-2 py-1 text-xs font-bold uppercase">
              Ready
            </span>
          </div>

          <label className="mt-5 block text-xs font-bold uppercase text-ink/60" htmlFor="quick-title">
            项目名称
          </label>
          <input
            id="quick-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            className="focus-ring mt-2 min-h-12 w-full rounded-md border border-ink/20 bg-white/78 px-4 font-bold text-ink"
          />

          <div className="mt-4">
            <OpenAIKeyPanel compact />
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2">
            {quickActions.map((action) => {
              const Icon = action.icon;
              const loading =
                action.mode === "new" ? busy : actionBusy === action.target;
              return (
                <button
                  key={action.label}
                  type="button"
                  onClick={() => runAction(action.target, action.mode)}
                  disabled={isNavigating}
                  className="focus-ring flex min-h-20 flex-col items-start justify-between rounded-md border border-ink/15 bg-white/58 p-3 text-left font-bold text-ink transition hover:border-ink/35 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <Icon size={18} aria-hidden="true" />
                  <span>
                    {loading ? "处理中" : action.label}
                    <span className="mt-1 block text-xs font-semibold text-ink/55">
                      {action.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          <button
            type="button"
            onClick={() => openDemo("options")}
            disabled={isNavigating}
            className="focus-ring mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-3 font-bold text-white transition hover:bg-tide disabled:cursor-not-allowed disabled:opacity-60"
          >
            打开完整示例
            <ArrowRight size={17} aria-hidden="true" />
          </button>
        </section>

        <footer className="absolute bottom-0 left-0 right-0 z-20 hidden border-t border-white/30 bg-white/40 px-6 py-3 backdrop-blur xl:block">
          <div className="mx-auto flex max-w-[1800px] items-center gap-4 text-xs font-bold uppercase text-ink/72">
            <CheckCircle2 size={16} aria-hidden="true" />
            Engine Ready
            <div className="h-1 flex-1 rounded bg-white/55">
              <div
                className="h-1 rounded bg-ink transition-all"
                style={{ width: `${(Number(activeCopy.progress.slice(0, 1)) / 5) * 100}%` }}
              />
            </div>
            <span>{activeCopy.progress}</span>
          </div>
        </footer>
      </section>
    </main>
  );
}
