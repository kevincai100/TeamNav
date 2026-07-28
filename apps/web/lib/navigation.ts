import { arrayMove } from "@dnd-kit/sortable";

export function faviconUrl(value: string): string | null {
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") return null;
    return `${url.origin}/favicon.ico`;
  } catch {
    return null;
  }
}

export function reorderItems<T extends { id: string; sort_order: number }>(
  items: T[],
  activeId: string,
  overId: string,
): T[] {
  const from = items.findIndex((item) => item.id === activeId);
  const to = items.findIndex((item) => item.id === overId);
  if (from < 0 || to < 0 || from === to) return items;
  return arrayMove(items, from, to).map((item, sort_order) => ({ ...item, sort_order }));
}

export function moveLinkBetweenCategories<
  L extends { id: string; category_id: string; sort_order: number },
  C extends { id: string; links: L[] },
>(categories: C[], activeId: string, targetCategoryId: string, overId?: string): C[] {
  const sourceCategory = categories.find((category) =>
    category.links.some((link) => link.id === activeId),
  );
  const targetCategory = categories.find((category) => category.id === targetCategoryId);
  const activeLink = sourceCategory?.links.find((link) => link.id === activeId);
  if (!sourceCategory || !targetCategory || !activeLink) return categories;

  const sourceLinks = sourceCategory.links.filter((link) => link.id !== activeId);
  const targetLinks = sourceCategory.id === targetCategory.id
    ? sourceLinks
    : targetCategory.links;
  const overIndex = overId ? targetLinks.findIndex((link) => link.id === overId) : -1;
  const insertAt = overIndex >= 0 ? overIndex : targetLinks.length;
  const movedLink = { ...activeLink, category_id: targetCategoryId };
  const nextTargetLinks = [
    ...targetLinks.slice(0, insertAt),
    movedLink,
    ...targetLinks.slice(insertAt),
  ].map((link, sort_order) => ({ ...link, sort_order }));
  const nextSourceLinks = sourceLinks.map((link, sort_order) => ({ ...link, sort_order }));

  return categories.map((category) => {
    if (category.id === targetCategoryId) return { ...category, links: nextTargetLinks };
    if (category.id === sourceCategory.id) return { ...category, links: nextSourceLinks };
    return category;
  }) as C[];
}
