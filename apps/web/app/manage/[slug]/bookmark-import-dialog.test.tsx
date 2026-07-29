// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api";

import { BookmarkImportDialog } from "./bookmark-import-dialog";

vi.mock("@/components/locale-provider", () => ({
  useI18n: () => ({
    t: (message: string, values?: Record<string, string | number>) =>
      Object.entries(values ?? {}).reduce(
        (result, [key, value]) => result.replace(`{${key}}`, String(value)),
        message,
      ),
  }),
}));

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, api: vi.fn() };
});

vi.mock("sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}));

const preview = {
  source_categories: 1,
  source_links: 2,
  accepted_links: 2,
  unsupported_links: 0,
  duplicate_links: 0,
  imported_links: 2,
  created_categories: 1,
  matched_categories: 0,
  capacity: {
    allowed: true,
    categories: { current: 0, importing: 1, after: 1, limit: 200, allowed: true },
    links: { current: 0, importing: 2, after: 2, limit: 2000, allowed: true },
  },
  categories: [
    {
      name: "Engineering",
      source_links: 2,
      imported_links: 2,
      existing: false,
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

function bookmarkFile() {
  const file = new File(["<DL><p></DL><p>"], "bookmarks.html", { type: "text/html" });
  Object.defineProperty(file, "text", {
    value: async () => "<DL><p></DL><p>",
  });
  return file;
}

describe("BookmarkImportDialog", () => {
  it("previews a file and confirms the exact import plan", async () => {
    vi.mocked(api)
      .mockResolvedValueOnce(preview)
      .mockResolvedValueOnce({ imported_links: 2 });
    const onImported = vi.fn(async () => undefined);
    const { container } = render(
      <BookmarkImportDialog slug="demo" csrf="csrf-token" onImported={onImported} />,
    );
    const input = container.querySelector<HTMLInputElement>('input[type="file"]');
    expect(input).not.toBeNull();

    fireEvent.change(input!, { target: { files: [bookmarkFile()] } });

    expect(await screen.findByRole("dialog")).toBeTruthy();
    expect(screen.getByText("容量检查通过")).toBeTruthy();
    expect(screen.getByText("Engineering")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "确认导入 2 项" }));

    await waitFor(() => expect(onImported).toHaveBeenCalledOnce());
    expect(api).toHaveBeenNthCalledWith(
      2,
      "/api/v1/manage/sites/demo/bookmarks/import",
      expect.objectContaining({
        method: "POST",
        headers: { "X-CSRF-Token": "csrf-token" },
      }),
    );
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("blocks confirmation when the capacity check fails", async () => {
    vi.mocked(api).mockResolvedValueOnce({
      ...preview,
      capacity: {
        ...preview.capacity,
        allowed: false,
        links: { ...preview.capacity.links, allowed: false, after: 2002 },
      },
    });
    const { container } = render(
      <BookmarkImportDialog slug="demo" csrf="csrf-token" onImported={vi.fn()} />,
    );
    const input = container.querySelector<HTMLInputElement>('input[type="file"]');

    fireEvent.change(input!, { target: { files: [bookmarkFile()] } });

    expect(await screen.findByText("容量不足，无法执行本次导入")).toBeTruthy();
    expect(
      (screen.getByRole("button", { name: "确认导入 2 项" }) as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(api).toHaveBeenCalledTimes(1);
  });
});
