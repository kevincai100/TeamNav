import type { NavLink } from "./types";

export const CATEGORY_LINK_PREVIEW_LIMIT = 12;

type CategoryDisplayOptions = {
  expanded: boolean;
  revealAll: boolean;
};

type CategoryDisplay = {
  links: NavLink[];
  hiddenCount: number;
  toggle: "expand" | "collapse" | null;
};

export function getCategoryDisplay(
  links: NavLink[],
  options: CategoryDisplayOptions,
): CategoryDisplay {
  if (options.revealAll) {
    return { links, hiddenCount: 0, toggle: null };
  }

  if (options.expanded) {
    return { links, hiddenCount: 0, toggle: "collapse" };
  }

  return {
    links: links.slice(0, CATEGORY_LINK_PREVIEW_LIMIT),
    hiddenCount: Math.max(0, links.length - CATEGORY_LINK_PREVIEW_LIMIT),
    toggle: links.length > CATEGORY_LINK_PREVIEW_LIMIT ? "expand" : null,
  };
}
