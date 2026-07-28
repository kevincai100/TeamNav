// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CategoryIconPicker } from "./category-icon-picker";

vi.mock("./locale-provider", () => ({
  useI18n: () => ({
    t: (message: string, values?: Record<string, string | number>) => Object.entries(values ?? {}).reduce(
      (result, [key, value]) => result.replace(`{${key}}`, String(value)),
      message,
    ),
  }),
}));

afterEach(cleanup);

function PickerHarness() {
  const [value, setValue] = useState("◎");
  return <CategoryIconPicker label="分类图标" value={value} onChange={setValue} />;
}

describe("CategoryIconPicker", () => {
  it("selects a preset symbol and closes the picker", () => {
    render(<PickerHarness />);

    fireEvent.click(screen.getByRole("button", { name: "分类图标" }));
    fireEvent.click(screen.getByRole("button", { name: "使用 ◇ 图标" }));

    expect(screen.getByRole("button", { name: "分类图标" }).textContent).toContain("◇");
    expect(screen.queryByRole("dialog", { name: "选择分类图标" })).toBeNull();
  });

  it("keeps a custom symbol input", () => {
    render(<PickerHarness />);

    fireEvent.click(screen.getByRole("button", { name: "分类图标" }));
    fireEvent.change(screen.getByRole("textbox", { name: "自定义图标" }), {
      target: { value: "☰" },
    });

    expect(screen.getByRole("button", { name: "分类图标" }).textContent).toContain("☰");
  });
});
