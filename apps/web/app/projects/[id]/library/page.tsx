import { LibraryClient } from "./LibraryClient";
import { PageShell } from "@/components/PageShell";
import { searchFloorplanLibrary } from "@/lib/api";
import type { FloorPlanLibrarySearchResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

async function loadInitialLibrary(): Promise<FloorPlanLibrarySearchResponse & { message?: string | null }> {
  try {
    const response = await searchFloorplanLibrary({
      query: "一家三口 收纳",
      bedrooms: 2,
      limit: 12
    });
    return { ...response, message: null };
  } catch (caught) {
    return {
      sources: [],
      items: [],
      message: caught instanceof Error ? caught.message : "户型库加载失败"
    };
  }
}

export default async function FloorplanLibraryPage({ params }: { params: { id: string } }) {
  const initial = await loadInitialLibrary();

  return (
    <PageShell projectId={params.id} current="library" title="检索户型库">
      <LibraryClient
        projectId={params.id}
        initialItems={initial.items}
        initialSources={initial.sources}
        initialMessage={initial.message}
      />
    </PageShell>
  );
}
