import type { LayoutConfig } from "@/lib/types";

export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  accent_color: "#167D68",
  canvas_style: "soft",
  card_style: "solid",
  content_width: "standard",
  columns: 3,
  density: "comfortable",
  header_alignment: "left",
  wallpaper_url: null,
  wallpaper_fit: "cover",
  wallpaper_position: "center",
  wallpaper_overlay: 40,
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

export function getWallpaperStyle(config: LayoutConfig) {
  if (!config.wallpaper_url) return undefined;

  let parsed: URL;
  try {
    parsed = new URL(config.wallpaper_url.trim());
  } catch {
    return undefined;
  }
  if (!["http:", "https:"].includes(parsed.protocol) || parsed.username || parsed.password) {
    return undefined;
  }

  const tiled = config.wallpaper_fit === "tile";
  return {
    backgroundImage: `url(${JSON.stringify(parsed.href)})`,
    backgroundPosition: `center ${config.wallpaper_position}`,
    backgroundRepeat: tiled ? "repeat" : "no-repeat",
    backgroundSize: tiled ? "auto" : config.wallpaper_fit,
  };
}
