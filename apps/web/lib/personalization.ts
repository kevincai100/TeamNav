import type { LayoutConfig } from "@/lib/types";

export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  accent_color: "#167D68",
  canvas_style: "soft",
  card_style: "solid",
  content_width: "standard",
  columns: 3,
  density: "comfortable",
  header_alignment: "left",
};

export const ACCENT_PRESETS = [
  "#167D68",
  "#2563EB",
  "#7C3AED",
  "#C2415D",
  "#C65D21",
  "#374151",
] as const;

export function normalizeLayoutConfig(config: Partial<LayoutConfig> | null | undefined): LayoutConfig {
  return { ...DEFAULT_LAYOUT_CONFIG, ...config };
}
