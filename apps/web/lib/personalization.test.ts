import { describe, expect, it } from "vitest";

import { DEFAULT_LAYOUT_CONFIG, normalizeLayoutConfig } from "./personalization";

describe("normalizeLayoutConfig", () => {
  it("fills defaults for existing workspaces", () => {
    expect(normalizeLayoutConfig({})).toEqual(DEFAULT_LAYOUT_CONFIG);
  });

  it("keeps supported personalized values", () => {
    expect(normalizeLayoutConfig({ accent_color: "#2563EB", columns: 3 })).toEqual({
      ...DEFAULT_LAYOUT_CONFIG,
      accent_color: "#2563EB",
      columns: 3,
    });
  });
});
