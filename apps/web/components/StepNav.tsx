"use client";

import Link from "next/link";
import { ClipboardList, ImageIcon, Library, MessageSquareText, Ruler, Sofa, Sparkles, Upload } from "lucide-react";

const steps = [
  { href: "upload", label: "上传", icon: Upload },
  { href: "library", label: "户型库", icon: Library },
  { href: "floorplan", label: "户型", icon: Ruler },
  { href: "brief", label: "需求", icon: MessageSquareText },
  { href: "options", label: "方案", icon: Sofa },
  { href: "living", label: "清单", icon: ClipboardList },
  { href: "coach", label: "助手", icon: Sparkles },
  { href: "renders", label: "渲染", icon: ImageIcon }
];

export function StepNav({ projectId, current }: { projectId: string; current: string }) {
  return (
    <nav className="flex min-w-0 flex-wrap items-center gap-2 lg:flex-1 lg:justify-end">
      {steps.map((step) => {
        const Icon = step.icon;
        const active = current === step.href;
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
