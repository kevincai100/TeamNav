import { describe, expect, it } from "vitest";

import { isFolderCollapsed } from "./folder-collapse";

describe("isFolderCollapsed", () => {
  it("re-evaluates the default when an import adds many folders", () => {
    const overrides = new Map<string, boolean>();

    expect(isFolderCollapsed(overrides, "folder", 2)).toBe(false);
    expect(isFolderCollapsed(overrides, "folder", 9)).toBe(true);
  });

  it("preserves a user's explicit expansion", () => {
    const overrides = new Map<string, boolean>([["folder", false]]);

    expect(isFolderCollapsed(overrides, "folder", 20)).toBe(false);
  });
});
