import type { Category } from "@/lib/types";

export function filterCategories(
  categories: Category[],
  query: string,
  categoryId: string | null,
): Category[] {
  const normalized = query.trim().toLocaleLowerCase();
  return categories
    .filter((category) => !categoryId || category.id === categoryId)
    .map((category) => ({
      ...category,
      links: category.links.filter((link) => {
        if (!normalized) return true;
        let domain = "";
        try {
          domain = new URL(link.url).hostname;
        } catch {
          domain = link.url;
        }
        return [link.name, link.description, category.name, domain, ...link.tags]
          .filter(Boolean)
          .some((value) => value!.toLocaleLowerCase().includes(normalized));
      }),
    }))
    .filter((category) => !normalized || category.links.length > 0);
}
