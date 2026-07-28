import { describe, expect, it } from "vitest";

import { faviconUrl, moveLinkBetweenCategories, reorderItems } from "./navigation";

describe("faviconUrl", () => {
  it("uses the origin favicon for HTTP links only", () => {
    expect(faviconUrl("https://docs.example.com/path?q=1")).toBe(
      "https://docs.example.com/favicon.ico",
    );
    expect(faviconUrl("mailto:hello@example.com")).toBeNull();
    expect(faviconUrl("javascript:alert(1)")).toBeNull();
  });
});

describe("reorderItems", () => {
  it("returns a new reindexed order", () => {
    const original = [
      { id: "a", sort_order: 0 },
      { id: "b", sort_order: 1 },
      { id: "c", sort_order: 2 },
    ];
    const result = reorderItems(original, "c", "a");
    expect(result.map((item) => [item.id, item.sort_order])).toEqual([
      ["c", 0],
      ["a", 1],
      ["b", 2],
    ]);
    expect(original.map((item) => item.id)).toEqual(["a", "b", "c"]);
  });
});

describe("moveLinkBetweenCategories", () => {
  it("moves a link before the drop target and reindexes both categories", () => {
    const categories = [
      {
        id: "source",
        sort_order: 0,
        links: [
          { id: "a", category_id: "source", sort_order: 0 },
          { id: "b", category_id: "source", sort_order: 1 },
        ],
      },
      {
        id: "target",
        sort_order: 1,
        links: [
          { id: "c", category_id: "target", sort_order: 0 },
          { id: "d", category_id: "target", sort_order: 1 },
        ],
      },
    ];

    const result = moveLinkBetweenCategories(categories, "b", "target", "d");

    expect(result[0].links).toEqual([{ id: "a", category_id: "source", sort_order: 0 }]);
    expect(result[1].links).toEqual([
      { id: "c", category_id: "target", sort_order: 0 },
      { id: "b", category_id: "target", sort_order: 1 },
      { id: "d", category_id: "target", sort_order: 2 },
    ]);
  });
});
