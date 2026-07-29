import { describe, expect, it } from "vitest";

import { filterCategories } from "./search";
import type { Category } from "./types";

const categories: Category[] = [
  {
    id: "development",
    name: "研发工具",
    description: null,
    icon: "D",
    sort_order: 0,
    is_visible: true,
    links: [
      {
        id: "github",
        category_id: "development",
        name: "GitHub",
        url: "https://github.com/teamnav",
        description: "代码托管",
        icon: "GH",
        tags: ["开发", "常用"],
        sort_order: 0,
        is_pinned: false,
        is_enabled: true,
        open_mode: "new",
        health_status: "unchecked",
        health_status_code: null,
        health_error: null,
        health_checked_at: null,
        health_consecutive_failures: 0,
      },
    ],
  },
  {
    id: "support",
    name: "客户支持",
    description: null,
    icon: "S",
    sort_order: 1,
    is_visible: true,
    links: [
      {
        id: "chat",
        category_id: "support",
        name: "Chatwoot",
        url: "https://chat.example.com",
        description: "客服工作台",
        icon: "CW",
        tags: ["客服"],
        sort_order: 0,
        is_pinned: false,
        is_enabled: true,
        open_mode: "new",
        health_status: "unchecked",
        health_status_code: null,
        health_error: null,
        health_checked_at: null,
        health_consecutive_failures: 0,
      },
    ],
  },
];

describe("navigation search", () => {
  it("matches names, descriptions, tags and domains without case sensitivity", () => {
    expect(filterCategories(categories, "GITHUB", null)[0].links[0].name).toBe("GitHub");
    expect(filterCategories(categories, "客服工作台", null)[0].links[0].name).toBe("Chatwoot");
    expect(filterCategories(categories, "example.com", null)[0].id).toBe("support");
  });

  it("combines the category tab with the search query", () => {
    expect(filterCategories(categories, "", "support")).toHaveLength(1);
    expect(filterCategories(categories, "GitHub", "support")).toHaveLength(0);
  });
});
