import { describe, expect, it } from "vitest";

import { getCategoryDisplay } from "./category-display";
import type { NavLink } from "./types";

function makeLinks(count: number): NavLink[] {
  return Array.from({ length: count }, (_, index) => ({
    id: `link-${index + 1}`,
    category_id: "category-1",
    name: `Link ${index + 1}`,
    url: `https://example.com/${index + 1}`,
    description: null,
    icon: "L",
    tags: [],
    sort_order: index,
    is_pinned: false,
    is_enabled: true,
    open_mode: "new",
  }));
}

describe("category display", () => {
  it("shows the first 12 links and reports the hidden remainder by default", () => {
    const result = getCategoryDisplay(makeLinks(15), {
      expanded: false,
      revealAll: false,
    });

    expect(result.links).toHaveLength(12);
    expect(result.links.at(-1)?.name).toBe("Link 12");
    expect(result.hiddenCount).toBe(3);
    expect(result.toggle).toBe("expand");
  });

  it("shows every link and offers collapse when the category is expanded", () => {
    const result = getCategoryDisplay(makeLinks(15), {
      expanded: true,
      revealAll: false,
    });

    expect(result.links).toHaveLength(15);
    expect(result.hiddenCount).toBe(0);
    expect(result.toggle).toBe("collapse");
  });

  it("shows every link without a toggle while search or category filtering reveals all", () => {
    const result = getCategoryDisplay(makeLinks(15), {
      expanded: false,
      revealAll: true,
    });

    expect(result.links).toHaveLength(15);
    expect(result.hiddenCount).toBe(0);
    expect(result.toggle).toBeNull();
  });

  it("does not offer a toggle when the category fits within the preview limit", () => {
    const result = getCategoryDisplay(makeLinks(12), {
      expanded: false,
      revealAll: false,
    });

    expect(result.links).toHaveLength(12);
    expect(result.hiddenCount).toBe(0);
    expect(result.toggle).toBeNull();
  });
});
