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
