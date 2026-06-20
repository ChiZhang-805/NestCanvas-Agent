import { z } from "zod";

export const pointSchema = z.tuple([z.number(), z.number()]);
export const polygonSchema = z.array(pointSchema).min(4);

export const roomSchema = z.object({
  id: z.string(),
  room_type: z.string(),
  polygon: polygonSchema,
  area_m2: z.number(),
  confidence: z.number()
});

export const openingSchema = z.object({
  id: z.string(),
  type: z.enum(["door", "window"]),
  wall_id: z.string().nullable().optional(),
  bbox: polygonSchema,
  width_m: z.number(),
  swing_direction: z.string().nullable().optional()
});

export const wallSchema = z.object({
  id: z.string(),
  centerline: z.array(pointSchema),
  thickness_m: z.number(),
  confidence: z.number(),
  load_bearing_status: z.string()
});

export const floorPlanSchema = z.object({
  id: z.string().optional(),
  project_id: z.string().optional(),
  version: z.string(),
  unit: z.literal("m"),
  scale_m_per_px: z.number(),
  boundary: polygonSchema,
  rooms: z.array(roomSchema),
  walls: z.array(wallSchema),
  doors: z.array(openingSchema),
  windows: z.array(openingSchema),
  warnings: z.array(z.string()),
  confidence: z.number()
});

export const floorPlanDatasetSourceSchema = z.object({
  id: z.string(),
  name: z.string(),
  url: z.string(),
  license: z.string(),
  commercial_use: z.enum(["allowed", "restricted", "unknown"]),
  recommended_use: z.string(),
  notes: z.array(z.string())
});

export const floorPlanLibraryItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  source_dataset_id: z.string(),
  source_dataset_name: z.string(),
  source_url: z.string(),
  license: z.string(),
  commercial_use: z.enum(["allowed", "restricted", "unknown"]),
  area_m2: z.number(),
  bedrooms: z.number(),
  bathrooms: z.number(),
  region: z.string(),
  tags: z.array(z.string()),
  household_fit: z.array(z.string()),
  match_score: z.number(),
  floorplan: floorPlanSchema
});

export const floorPlanLibrarySearchResponseSchema = z.object({
  sources: z.array(floorPlanDatasetSourceSchema),
  items: z.array(floorPlanLibraryItemSchema)
});

export const designBriefSchema = z.object({
  id: z.string().optional(),
  project_id: z.string().optional(),
  style: z.string(),
  budget_cny: z.number().nullable().optional(),
  residents: z.array(z.string()),
  room_priorities: z.array(z.string()),
  must_have: z.array(z.string()),
  avoid: z.array(z.string()),
  storage_level: z.enum(["low", "medium", "high"]),
  color_palette: z.array(z.string()),
  constraints: z.array(z.string())
});

export const furnitureItemSchema = z.object({
  id: z.string(),
  category: z.string(),
  room_id: z.string(),
  bbox: polygonSchema,
  rotation_deg: z.number(),
  dimensions_m: pointSchema,
  clearance_m: z.number(),
  material_hint: z.string().nullable().optional()
});

export const layoutOptionSchema = z.object({
  id: z.string(),
  project_id: z.string().optional(),
  floorplan_id: z.string().optional(),
  brief_id: z.string().optional(),
  strategy: z.enum(["balanced_storage", "open_living", "family_friendly"]),
  furniture_items: z.array(furnitureItemSchema),
  score: z.number(),
  hard_errors: z.array(z.string()),
  soft_warnings: z.array(z.string()),
  metrics: z.record(z.unknown())
});

export const layoutOptionReviewSchema = z.object({
  option_id: z.string(),
  strategy: z.string(),
  headline: z.string(),
  scores: z.record(z.number()),
  strengths: z.array(z.string()),
  concerns: z.array(z.string()),
  suggestions: z.array(z.string())
});

export const designReviewSchema = z.object({
  project_id: z.string(),
  generated_with: z.enum(["local_rules", "openai", "mock"]),
  summary: z.string(),
  best_option_id: z.string().nullable().optional(),
  readiness_score: z.number(),
  global_risks: z.array(z.string()),
  next_questions: z.array(z.string()),
  option_reviews: z.array(layoutOptionReviewSchema)
});

export const livingBudgetPhaseSchema = z.object({
  key: z.enum(["move_in_essentials", "comfort_upgrade", "style_finish", "optional_later"]),
  label: z.string(),
  estimated_budget_cny_min: z.number(),
  estimated_budget_cny_max: z.number(),
  included_categories: z.array(z.string()),
  notes: z.array(z.string())
});

export const livingShoppingItemSchema = z.object({
  category: z.string(),
  label: z.string(),
  room_id: z.string(),
  room_type: z.string(),
  priority: z.enum(["must_buy", "reuse_or_buy", "optional"]),
  dimensions_m: pointSchema,
  estimated_price_cny_low: z.number(),
  estimated_price_cny_high: z.number(),
  search_keywords: z.array(z.string()),
  material_hint: z.string().nullable().optional(),
  why: z.string()
});

export const livingDiscussionCardSchema = z.object({
  topic: z.string(),
  prompt: z.string(),
  related_rooms: z.array(z.string()),
  decision_hint: z.string()
});

export const livingPlanPackageSchema = z.object({
  project_id: z.string(),
  selected_option_id: z.string(),
  selected_strategy: z.string(),
  generated_with: z.literal("local_rules"),
  household_summary: z.string(),
  recommended_next_step: z.string(),
  budget_total_low_cny: z.number(),
  budget_total_high_cny: z.number(),
  budget_fit: z.enum(["within_budget", "tight", "over_budget", "unknown"]),
  budget_phases: z.array(livingBudgetPhaseSchema),
  shopping_items: z.array(livingShoppingItemSchema),
  reuse_candidates: z.array(z.string()),
  family_discussion_cards: z.array(livingDiscussionCardSchema),
  designer_handoff_questions: z.array(z.string()),
  caveats: z.array(z.string())
});

export const portableServiceSpecSchema = z.object({
  key: z.string(),
  label: z.string(),
  service_type: z.enum(["api", "worker", "cli", "export"]),
  purpose: z.string(),
  inputs: z.array(z.string()),
  outputs: z.array(z.string()),
  status: z.enum(["ready", "planned", "blocked"])
});

export const workflowStepSchema = z.object({
  key: z.string(),
  label: z.string(),
  status: z.enum(["done", "current", "available", "blocked"]),
  artifact_count: z.number(),
  blockers: z.array(z.string()),
  next_actions: z.array(z.string()),
  automation_hint: z.string()
});

export const projectWorkflowSchema = z.object({
  project_id: z.string(),
  current_step: z.string(),
  readiness_score: z.number(),
  summary: z.string(),
  steps: z.array(workflowStepSchema),
  automation_plan: z.array(z.string()),
  llm_modules: z.array(portableServiceSpecSchema),
  portable_services: z.array(portableServiceSpecSchema)
});

export const homeCoachRoomCardSchema = z.object({
  room_id: z.string(),
  room_type: z.string(),
  headline: z.string(),
  current_furniture: z.array(z.string()),
  daily_use_notes: z.array(z.string()),
  risks: z.array(z.string()),
  shopping_focus: z.array(z.string()),
  measurement_tasks: z.array(z.string()),
  visual_prompt: z.string()
});

export const homeCoachPackageSchema = z.object({
  project_id: z.string(),
  generated_with: z.literal("local_rules"),
  summary: z.string(),
  workflow: projectWorkflowSchema,
  selected_option_id: z.string().nullable().optional(),
  room_cards: z.array(homeCoachRoomCardSchema),
  family_script: z.array(z.string()),
  designer_packet: z.array(z.string()),
  llm_upgrade_plan: z.array(portableServiceSpecSchema),
  portable_services: z.array(portableServiceSpecSchema),
  caveats: z.array(z.string())
});

export const renderAssetSchema = z.object({
  id: z.string(),
  project_id: z.string().optional(),
  status: z.string(),
  prompt: z.string(),
  input_option_id: z.string(),
  output_path: z.string(),
  disclaimer: z.string()
});

export const assetSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  asset_type: z.enum(["image", "pdf", "prepared_image", "render", "export"]),
  local_path: z.string(),
  mime_type: z.string(),
  width: z.number().nullable().optional(),
  height: z.number().nullable().optional(),
  metadata: z.record(z.unknown()).optional(),
  created_at: z.string().nullable().optional()
});

export const inputPreparationResultSchema = z.object({
  project_id: z.string(),
  source_asset_id: z.string(),
  prepared_asset: assetSchema,
  quality_score: z.number(),
  preparation_stage: z.enum(["prepared", "passthrough"]),
  detected_content: z.enum(["floorplan_like", "document_like", "unknown"]),
  operations: z.array(z.string()),
  warnings: z.array(z.string()),
  suggestions: z.array(z.string()),
  vision_notes: z.array(z.string()),
  crop_bbox_px: z.array(z.number()).nullable().optional(),
  perspective_corrected: z.boolean()
});

export const projectDetailSchema = z.object({
  id: z.string(),
  title: z.string(),
  created_at: z.string(),
  status: z.string(),
  assets: z.array(assetSchema),
  floorplans: z.array(floorPlanSchema),
  briefs: z.array(designBriefSchema),
  layout_options: z.array(layoutOptionSchema),
  renders: z.array(renderAssetSchema)
});

export const openAISettingsStatusSchema = z.object({
  active: z.boolean(),
  source: z.enum(["browser", "env", "mock"]),
  env_key_configured: z.boolean(),
  request_key_configured: z.boolean(),
  text_model: z.string(),
  fast_model: z.string(),
  image_model: z.string()
});

export type Point = z.infer<typeof pointSchema>;
export type Room = z.infer<typeof roomSchema>;
export type FloorPlan = z.infer<typeof floorPlanSchema>;
export type FloorPlanDatasetSource = z.infer<typeof floorPlanDatasetSourceSchema>;
export type FloorPlanLibraryItem = z.infer<typeof floorPlanLibraryItemSchema>;
export type FloorPlanLibrarySearchResponse = z.infer<typeof floorPlanLibrarySearchResponseSchema>;
export type DesignBrief = z.infer<typeof designBriefSchema>;
export type FurnitureItem = z.infer<typeof furnitureItemSchema>;
export type LayoutOption = z.infer<typeof layoutOptionSchema>;
export type LayoutOptionReview = z.infer<typeof layoutOptionReviewSchema>;
export type DesignReview = z.infer<typeof designReviewSchema>;
export type LivingBudgetPhase = z.infer<typeof livingBudgetPhaseSchema>;
export type LivingShoppingItem = z.infer<typeof livingShoppingItemSchema>;
export type LivingDiscussionCard = z.infer<typeof livingDiscussionCardSchema>;
export type LivingPlanPackage = z.infer<typeof livingPlanPackageSchema>;
export type PortableServiceSpec = z.infer<typeof portableServiceSpecSchema>;
export type WorkflowStep = z.infer<typeof workflowStepSchema>;
export type ProjectWorkflow = z.infer<typeof projectWorkflowSchema>;
export type HomeCoachRoomCard = z.infer<typeof homeCoachRoomCardSchema>;
export type HomeCoachPackage = z.infer<typeof homeCoachPackageSchema>;
export type RenderAsset = z.infer<typeof renderAssetSchema>;
export type Asset = z.infer<typeof assetSchema>;
export type InputPreparationResult = z.infer<typeof inputPreparationResultSchema>;
export type ProjectDetail = z.infer<typeof projectDetailSchema>;
export type OpenAISettingsStatus = z.infer<typeof openAISettingsStatusSchema>;

export type JobStatus = {
  id: string;
  status: string;
  stage: string;
  progress: number;
  result_id: string | null;
  error: string | null;
};
