import Link from "next/link";
import { Home } from "lucide-react";
import { OpenAIKeyPanel } from "@/components/OpenAIKeyPanel";
import { StepNav } from "@/components/StepNav";

export function PageShell({
  projectId,
  current,
  title,
  children
}: {
  projectId: string;
  current: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <main className="flex h-[100svh] min-h-0 flex-col overflow-hidden bg-[#f2f4f1]">
      <header className="z-30 shrink-0 border-b border-ink/10 bg-white/86 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
          <Link href="/" className="focus-ring inline-flex items-center gap-2 rounded-md text-ink">
            <Home size={18} aria-hidden="true" />
            <span className="font-bold">NestCanvas Agent（栖画）</span>
          </Link>
          <StepNav projectId={projectId} current={current} />
        </div>
      </header>
      <section data-shell-content className="mx-auto min-h-0 w-full max-w-7xl flex-1 overflow-y-auto overflow-x-hidden px-5 py-7">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-bold uppercase text-clay">Project studio</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink sm:text-3xl">{title}</h1>
          </div>
          <span className="max-w-full truncate rounded-md border border-ink/10 bg-white px-3 py-2 text-xs font-semibold text-ink/58">
            {projectId}
          </span>
        </div>
        <div className="mt-5 max-w-3xl">
          <OpenAIKeyPanel compact />
        </div>
        <div className="mt-6">{children}</div>
      </section>
    </main>
  );
}
