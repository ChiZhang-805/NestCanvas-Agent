"use client";

import Link from "next/link";
import { Home, Library, Settings, Sparkles, Upload, WandSparkles } from "lucide-react";
import { usePathname } from "next/navigation";
import { StepNav } from "@/components/StepNav";

const utilityLinks = [
  { label: "首页", href: "/", icon: Home },
  { label: "设置", href: "/settings", icon: Settings },
  { label: "上传", href: "upload", icon: Upload },
  { label: "户型库", href: "library", icon: Library },
  { label: "助手", href: "coach", icon: Sparkles }
];

export function PageShell({
  projectId,
  current,
  title,
  currentStepReady,
  children
}: {
  projectId: string;
  current: string;
  title: string;
  currentStepReady?: boolean;
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <main className="flex h-[100svh] min-h-0 flex-col overflow-hidden bg-[#f2f4f1] text-ink">
      <header className="z-40 shrink-0 border-b border-ink/10 bg-white/[0.88] shadow-[0_8px_28px_rgba(34,49,44,0.05)] backdrop-blur">
        <div className="flex w-full flex-col gap-3 px-5 py-3 lg:flex-row lg:items-center lg:justify-between">
          <Link href="/" className="focus-ring flex shrink-0 items-center gap-3 rounded-md text-ink">
            <span className="flex size-10 shrink-0 items-center justify-center rounded-md border border-tide/20 bg-tide/10 text-tide">
              <WandSparkles size={20} aria-hidden="true" />
            </span>
            <span>
              <span className="block text-base font-black leading-5">NestCanvas Agent（栖画）</span>
              <span className="block text-xs font-semibold text-ink/55">Home design canvas</span>
            </span>
          </Link>
          <StepNav projectId={projectId} current={current} currentStepReady={currentStepReady} />
        </div>
      </header>
      <div className="flex min-h-0 w-full flex-1 overflow-hidden px-5">
        <aside className="hidden w-32 shrink-0 overflow-y-auto border-r border-ink/10 py-5 pr-3 xl:block">
          <nav className="grid gap-2">
            {utilityLinks.map((link) => {
              const Icon = link.icon;
              const href = link.href.startsWith("/") ? link.href : `/projects/${projectId}/${link.href}`;
              const active = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <Link
                  key={`${link.label}-${link.href}`}
                  href={href}
                  className={`focus-ring flex min-h-10 items-center gap-2 rounded-md border px-3 text-sm font-bold transition ${
                    active ? "border-tide bg-tide text-white" : "border-ink/10 bg-white text-ink hover:border-tide"
                  }`}
                >
                  <Icon size={15} aria-hidden="true" />
                  <span>{link.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        <div data-shell-content className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden py-5 xl:pl-5">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <h1 className="text-3xl font-black leading-tight text-ink sm:text-4xl">{title}</h1>
          </div>
          <div className="mt-5">{children}</div>
        </div>
      </div>
    </main>
  );
}
