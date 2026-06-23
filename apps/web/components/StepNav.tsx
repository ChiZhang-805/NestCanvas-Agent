"use client";

import Link from "next/link";
import { ClipboardList, ImageIcon, MessageSquareText, Ruler, Sofa, Upload } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { getProject } from "@/lib/api";
import type { ProjectDetail } from "@/lib/types";
import { PROJECT_UPDATED_EVENT } from "@/lib/projectEvents";

const steps = [
  { href: "upload", label: "上传", icon: Upload },
  { href: "floorplan", label: "户型", icon: Ruler },
  { href: "brief", label: "需求", icon: MessageSquareText },
  { href: "options", label: "方案", icon: Sofa },
  { href: "living", label: "清单", icon: ClipboardList },
  { href: "renders", label: "渲染", icon: ImageIcon }
];

function isStepCompleted(project: ProjectDetail | null, href: string) {
  if (!project) return false;
  if (href === "upload") return project.floorplans.length > 0;
  if (href === "floorplan") return project.floorplans.length > 0;
  if (href === "brief") return project.briefs.length > 0;
  if (href === "options") return project.layout_options.length > 0;
  if (href === "living") return project.layout_options.length > 0;
  if (href === "renders") return project.renders.length > 0;
  return false;
}

export function StepNav({
  projectId,
  current,
  currentStepReady
}: {
  projectId: string;
  current: string;
  currentStepReady?: boolean;
}) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const activeIndex = steps.findIndex((step) => step.href === current);

  const loadProject = useCallback(async () => {
    try {
      setProject(await getProject(projectId));
    } catch {
      setProject(null);
    }
  }, [projectId]);

  useEffect(() => {
    loadProject();
  }, [loadProject]);

  useEffect(() => {
    const refresh = (event?: Event) => {
      const customEvent = event as CustomEvent<{ projectId?: string }> | undefined;
      if (!customEvent?.detail?.projectId || customEvent.detail.projectId === projectId) {
        loadProject();
      }
    };
    window.addEventListener(PROJECT_UPDATED_EVENT, refresh);
    window.addEventListener("focus", refresh);
    return () => {
      window.removeEventListener(PROJECT_UPDATED_EVENT, refresh);
      window.removeEventListener("focus", refresh);
    };
  }, [loadProject, projectId]);

  function isAllowed(index: number) {
    if (index === 0) return true;
    if (index === activeIndex) return true;
    if (activeIndex >= 0 && index < activeIndex) return true;
    if (activeIndex >= 0 && index > activeIndex && currentStepReady === false) return false;
    return steps.slice(0, index).every((step, stepIndex) => {
      if (stepIndex === activeIndex && currentStepReady !== undefined) return currentStepReady;
      return isStepCompleted(project, step.href);
    });
  }

  return (
    <nav className="flex min-w-0 flex-wrap items-center gap-2 lg:flex-1 lg:justify-end">
      {steps.map((step, index) => {
        const Icon = step.icon;
        const active = current === step.href;
        const allowed = isAllowed(index);
        if (!allowed) {
          return (
            <button
              key={step.href}
              type="button"
              disabled
              title="请先保存当前环节"
              className="focus-ring inline-flex min-h-10 cursor-not-allowed items-center gap-2 rounded-md border border-ink/10 bg-white px-3 py-2 text-sm font-bold tracking-normal text-ink/35 opacity-70"
            >
              <Icon size={16} aria-hidden="true" />
              {step.label}
            </button>
          );
        }
        return (
          <Link
            key={step.href}
            href={`/projects/${projectId}/${step.href}`}
            className={`focus-ring inline-flex min-h-10 items-center gap-2 rounded-md border px-3 py-2 text-sm font-bold tracking-normal transition ${
              active
                ? "border-tide bg-tide text-white"
                : "border-ink/10 bg-white text-ink hover:border-tide"
            }`}
          >
            <Icon size={16} aria-hidden="true" />
            {step.label}
          </Link>
        );
      })}
    </nav>
  );
}
