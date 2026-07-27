import { describe, expect, it } from "vitest";

import {
  DEFAULT_LAYOUT_CONFIG,
  getWallpaperStyle,
  normalizeLayoutConfig,
} from "./personalization";

describe("normalizeLayoutConfig", () => {
  it("fills defaults for existing workspaces", () => {
    expect(normalizeLayoutConfig({})).toEqual(DEFAULT_LAYOUT_CONFIG);
  });

  it("keeps supported personalized values", () => {
    expect(normalizeLayoutConfig({
      accent_color: "#2563EB",
      columns: 3,
      wallpaper_url: "https://cdn.example.com/team-wallpaper.jpg",
      wallpaper_fit: "contain",
      wallpaper_position: "bottom",
      wallpaper_overlay: 55,
    })).toEqual({
      ...DEFAULT_LAYOUT_CONFIG,
      accent_color: "#2563EB",
      columns: 3,
      wallpaper_url: "https://cdn.example.com/team-wallpaper.jpg",
      wallpaper_fit: "contain",
      wallpaper_position: "bottom",
      wallpaper_overlay: 55,
    });
  });
});

describe("getWallpaperStyle", () => {
  it("creates a safely quoted remote background style", () => {
    expect(getWallpaperStyle(normalizeLayoutConfig({
      wallpaper_url: "https://cdn.example.com/team wallpaper(1).jpg",
      wallpaper_fit: "cover",
      wallpaper_position: "top",
    }))).toEqual({
      backgroundImage: 'url("https://cdn.example.com/team%20wallpaper(1).jpg")',
      backgroundPosition: "center top",
      backgroundRepeat: "no-repeat",
      backgroundSize: "cover",
    });
  });

  it.each(["javascript:alert(1)", "data:image/png;base64,abc", "//example.com/a.jpg"])(
    "rejects an unsafe wallpaper URL: %s",
    (wallpaperUrl) => {
      expect(getWallpaperStyle(normalizeLayoutConfig({ wallpaper_url: wallpaperUrl }))).toBeUndefined();
    },
  );
});
