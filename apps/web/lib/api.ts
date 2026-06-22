import {
  Asset,
  DesignBrief,
  DesignReview,
  FloorPlan,
  FloorPlanLibrarySearchResponse,
  HomeCoachPackage,
  InputPreparationResult,
  JobStatus,
  LayoutOption,
  LivingPlanPackage,
  OpenAISettingsStatus,
  ProjectDetail,
  ProjectWorkflow,
  RenderAsset,
  assetSchema,
  designBriefSchema,
  designReviewSchema,
  floorPlanSchema,
  floorPlanLibrarySearchResponseSchema,
  homeCoachPackageSchema,
  inputPreparationResultSchema,
  layoutOptionSchema,
  livingPlanPackageSchema,
  openAISettingsStatusSchema,
  projectDetailSchema,
  projectWorkflowSchema,
  renderAssetSchema
} from "@/lib/types";

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

export const API_BASE = configuredApiBase
  ? configuredApiBase.replace(/\/$/, "")
  : "";

export const OPENAI_API_KEY_STORAGE_KEY = "nestcanvas.openai_api_key";
export const OPENAI_MODEL_TEXT_STORAGE_KEY = "nestcanvas.openai_model_text";
export const OPENAI_MODEL_FAST_STORAGE_KEY = "nestcanvas.openai_model_fast";
export const OPENAI_MODEL_IMAGE_STORAGE_KEY = "nestcanvas.openai_model_image";

function apiUrl(path: string) {
  return `${API_BASE}${path}`;
}

function summarizeResponseError(status: number, statusText: string, contentType: string | null, detail: string) {
  const trimmed = detail.trim();
  if (contentType?.includes("text/html") || trimmed.startsWith("<!DOCTYPE") || trimmed.startsWith("<html")) {
    return `后端 API 暂时不可用（HTTP ${status}${statusText ? ` ${statusText}` : ""}）。如果使用 Render Free plan，可能正在冷启动；稍后刷新或检查 nestcanvas-api 服务状态。`;
  }
  if (!trimmed) return `Request failed: ${status}${statusText ? ` ${statusText}` : ""}`;
  return trimmed.length > 280 ? `${trimmed.slice(0, 280)}...` : trimmed;
}

export function backendAssetUrl(path: string | null | undefined) {
  if (!path) return path;
  if (/^https?:\/\//i.test(path) || path.startsWith("data:")) return path;
  return apiUrl(path.startsWith("/") ? path : `/${path}`);
}

export function getStoredOpenAISettings() {
  if (typeof window === "undefined") return { apiKey: "", modelText: "", modelFast: "", modelImage: "" };
  try {
    return {
      apiKey: window.localStorage.getItem(OPENAI_API_KEY_STORAGE_KEY) ?? "",
      modelText: window.localStorage.getItem(OPENAI_MODEL_TEXT_STORAGE_KEY) ?? "",
      modelFast: window.localStorage.getItem(OPENAI_MODEL_FAST_STORAGE_KEY) ?? "",
      modelImage: window.localStorage.getItem(OPENAI_MODEL_IMAGE_STORAGE_KEY) ?? ""
    };
  } catch {
    return { apiKey: "", modelText: "", modelFast: "", modelImage: "" };
  }
}

export function getStoredOpenAIKey(): string {
  return getStoredOpenAISettings().apiKey;
}

function setStoredValue(key: string, value: string | undefined) {
  if (typeof window === "undefined" || value === undefined) return;
  const cleaned = value.trim();
  try {
    if (cleaned) {
      window.localStorage.setItem(key, cleaned);
    } else {
      window.localStorage.removeItem(key);
    }
  } catch {
    // The app still works with .env keys or mock mode when localStorage is unavailable.
  }
}

export function saveStoredOpenAISettings(payload: {
  apiKey?: string;
  modelText?: string;
  modelFast?: string;
  modelImage?: string;
}) {
  setStoredValue(OPENAI_API_KEY_STORAGE_KEY, payload.apiKey);
  setStoredValue(OPENAI_MODEL_TEXT_STORAGE_KEY, payload.modelText);
  setStoredValue(OPENAI_MODEL_FAST_STORAGE_KEY, payload.modelFast);
  setStoredValue(OPENAI_MODEL_IMAGE_STORAGE_KEY, payload.modelImage);
}

export function saveStoredOpenAIKey(value: string) {
  saveStoredOpenAISettings({ apiKey: value });
}

function openAIHeader(): Record<string, string> {
  const stored = getStoredOpenAISettings();
  return {
    ...(stored.apiKey ? { "X-OpenAI-API-Key": stored.apiKey } : {}),
    ...(stored.modelText ? { "X-OpenAI-Model-Text": stored.modelText } : {}),
    ...(stored.modelFast ? { "X-OpenAI-Model-Fast": stored.modelFast } : {}),
    ...(stored.modelImage ? { "X-OpenAI-Model-Image": stored.modelImage } : {})
  };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...openAIHeader(),
      ...init?.headers
    }
  });
  if (!response.ok) {
    const detail = await response.text();
    let message = summarizeResponseError(
      response.status,
      response.statusText,
      response.headers.get("content-type"),
      detail
    );
    try {
      const parsed = JSON.parse(detail) as { detail?: unknown };
      if (typeof parsed.detail === "string") {
        message = parsed.detail;
      }
    } catch {
      // Keep the raw response body when it is not JSON.
    }
    throw new Error(message);
  }
  const contentType = response.headers.get("content-type");
  if (!contentType?.includes("application/json")) {
    const detail = await response.text();
    throw new Error(summarizeResponseError(response.status, response.statusText, contentType, detail));
  }
  return (await response.json()) as T;
}

export async function createProject(title: string) {
  return request<{ id: string; title: string; status: string; created_at: string }>(
    "/api/projects",
    {
      method: "POST",
      body: JSON.stringify({ title })
    }
  );
}

export async function createDemoProject(): Promise<ProjectDetail> {
  const payload = await request<unknown>("/api/demo-project", {
    method: "POST"
  });
  return projectDetailSchema.parse(payload);
}

export async function getOpenAISettingsStatus(): Promise<OpenAISettingsStatus> {
  const payload = await request<unknown>("/api/settings/openai");
  return openAISettingsStatusSchema.parse(payload);
}

export async function getProject(projectId: string): Promise<ProjectDetail> {
  const payload = await request<unknown>(`/api/projects/${projectId}`);
  return projectDetailSchema.parse(payload);
}

export async function getProjectWorkflow(projectId: string): Promise<ProjectWorkflow> {
  const payload = await request<unknown>(`/api/projects/${projectId}/workflow`);
  return projectWorkflowSchema.parse(payload);
}

export async function searchFloorplanLibrary(params: {
  query?: string;
  bedrooms?: number;
  minArea?: number;
  maxArea?: number;
  dataset?: string;
  tags?: string;
  limit?: number;
} = {}): Promise<FloorPlanLibrarySearchResponse> {
  const search = new URLSearchParams();
  if (params.query) search.set("query", params.query);
  if (params.bedrooms !== undefined) search.set("bedrooms", String(params.bedrooms));
  if (params.minArea !== undefined) search.set("min_area", String(params.minArea));
  if (params.maxArea !== undefined) search.set("max_area", String(params.maxArea));
  if (params.dataset) search.set("dataset", params.dataset);
  if (params.tags) search.set("tags", params.tags);
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  const payload = await request<unknown>(`/api/floorplan-library${suffix}`);
  return floorPlanLibrarySearchResponseSchema.parse(payload);
}

export async function uploadAsset(projectId: string, file: File) {
  const data = new FormData();
  data.append("file", file);
  return request<unknown>(`/api/projects/${projectId}/assets`, {
    method: "POST",
    body: data
  });
}

export async function prepareInput(projectId: string): Promise<InputPreparationResult> {
  const payload = await request<unknown>(`/api/projects/${projectId}/prepare-input`, {
    method: "POST"
  });
  return inputPreparationResultSchema.parse(payload);
}

export async function createStarterFloorplan(projectId: string): Promise<FloorPlan> {
  const payload = await request<unknown>(`/api/projects/${projectId}/starter-floorplan`, {
    method: "POST"
  });
  return floorPlanSchema.parse(payload);
}

export async function createLibraryFloorplan(
  projectId: string,
  templateId: string
): Promise<FloorPlan> {
  const payload = await request<unknown>(
    `/api/projects/${projectId}/library-floorplan/${templateId}`,
    {
      method: "POST"
    }
  );
  return floorPlanSchema.parse(payload);
}

export async function exportProject(projectId: string): Promise<Asset> {
  const payload = await request<unknown>(`/api/projects/${projectId}/export`, {
    method: "POST"
  });
  return assetSchema.parse(payload);
}

export async function parseFloorplan(projectId: string) {
  return request<{ job_id: string }>(`/api/projects/${projectId}/parse-floorplan`, {
    method: "POST"
  });
}

export async function getJob(jobId: string): Promise<JobStatus> {
  return request<JobStatus>(`/api/jobs/${jobId}`);
}

export async function getFloorplan(floorplanId: string): Promise<FloorPlan> {
  const payload = await request<unknown>(`/api/floorplans/${floorplanId}`);
  return floorPlanSchema.parse(payload);
}

export async function patchFloorplan(floorplanId: string, floorplan: FloorPlan) {
  const { id: _id, project_id: _projectId, ...body } = floorplan;
  const payload = await request<unknown>(`/api/floorplans/${floorplanId}`, {
    method: "PATCH",
    body: JSON.stringify(body)
  });
  return floorPlanSchema.parse(payload);
}

export async function createBrief(
  projectId: string,
  text: string
): Promise<DesignBrief> {
  const payload = await request<unknown>(`/api/projects/${projectId}/brief`, {
    method: "POST",
    body: JSON.stringify({ text })
  });
  return designBriefSchema.parse(payload);
}

export async function createLayoutOptions(
  projectId: string
): Promise<LayoutOption[]> {
  const payload = await request<unknown>(`/api/projects/${projectId}/layout-options`, {
    method: "POST"
  });
  return layoutOptionSchema.array().parse(payload);
}

export async function createDesignReview(projectId: string): Promise<DesignReview> {
  const payload = await request<unknown>(`/api/projects/${projectId}/design-review`, {
    method: "POST"
  });
  return designReviewSchema.parse(payload);
}

export async function createLivingPlan(projectId: string): Promise<LivingPlanPackage> {
  const payload = await request<unknown>(`/api/projects/${projectId}/living-plan`, {
    method: "POST"
  });
  return livingPlanPackageSchema.parse(payload);
}

export async function createHomeCoach(projectId: string): Promise<HomeCoachPackage> {
  const payload = await request<unknown>(`/api/projects/${projectId}/home-coach`, {
    method: "POST"
  });
  return homeCoachPackageSchema.parse(payload);
}

export async function renderOption(optionId: string): Promise<RenderAsset> {
  const payload = await request<unknown>(`/api/layout-options/${optionId}/render`, {
    method: "POST"
  });
  return renderAssetSchema.parse(payload);
}

export async function listRenders(projectId: string): Promise<RenderAsset[]> {
  const payload = await request<unknown>(`/api/projects/${projectId}/renders`);
  return renderAssetSchema.array().parse(payload);
}

export function toAssetUrl(outputPath: string): string {
  if (outputPath.startsWith("http://") || outputPath.startsWith("https://")) {
    return outputPath;
  }

  const normalized = outputPath.replace(/\\/g, "/");
  const marker = "/storage/";
  const index = normalized.indexOf(marker);
  if (index >= 0) {
    return `${API_BASE}${normalized.slice(index)}`;
  }

  const relativeMarker = "storage/";
  const relativeIndex = normalized.indexOf(relativeMarker);
  if (relativeIndex >= 0) {
    return `${API_BASE}/${normalized.slice(relativeIndex)}`;
  }

  const rendersMarker = "/renders/";
  const rendersIndex = normalized.indexOf(rendersMarker);
  if (rendersIndex >= 0) {
    return `${API_BASE}/storage${normalized.slice(rendersIndex)}`;
  }
  return normalized;
}
