export const PROJECT_UPDATED_EVENT = "nestcanvas:project-updated";

export function notifyProjectUpdated(projectId: string) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(PROJECT_UPDATED_EVENT, { detail: { projectId } }));
}
