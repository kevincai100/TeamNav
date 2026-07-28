// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { CategoryTabs } from "./category-tabs";

const categories = [
  { id: "one", icon: "1", name: "One" },
  { id: "two", icon: "2", name: "Two" },
];

beforeAll(() => {
  if (!window.PointerEvent) window.PointerEvent = MouseEvent as typeof PointerEvent;
});

afterEach(cleanup);

describe("CategoryTabs", () => {
  it("keeps a normal tab click native until the pointer becomes a drag", () => {
    const onSelect = vi.fn();
    render(
      <CategoryTabs
        categories={categories}
        activeId={null}
        allLabel="All"
        ariaLabel="Category filter"
        onSelect={onSelect}
      />,
    );
    const tablist = screen.getByRole("tablist", { name: "Category filter" });
    const setPointerCapture = vi.fn();
    tablist.setPointerCapture = setPointerCapture;

    fireEvent.pointerDown(screen.getByRole("tab", { name: "One" }), {
      pointerId: 1,
      pointerType: "mouse",
      clientX: 100,
    });

    expect(setPointerCapture).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("tab", { name: "One" }));
    expect(onSelect).toHaveBeenCalledWith("one");
  });

  it("scrolls horizontally when dragged with a mouse", () => {
    render(
      <CategoryTabs
        categories={categories}
        activeId={null}
        allLabel="All"
        ariaLabel="Category filter"
        onSelect={vi.fn()}
      />,
    );
    const tablist = screen.getByRole("tablist", { name: "Category filter" });

    fireEvent.pointerDown(tablist, { pointerId: 1, pointerType: "mouse", clientX: 100 });
    fireEvent.pointerMove(tablist, { pointerId: 1, pointerType: "mouse", clientX: 40 });
    fireEvent.pointerUp(tablist, { pointerId: 1, pointerType: "mouse", clientX: 40 });

    expect(tablist.scrollLeft).toBe(60);
  });

  it("turns a vertical wheel gesture into horizontal scrolling", () => {
    render(
      <CategoryTabs
        categories={categories}
        activeId={null}
        allLabel="All"
        ariaLabel="Category filter"
        onSelect={vi.fn()}
      />,
    );
    const tablist = screen.getByRole("tablist", { name: "Category filter" });

    fireEvent.wheel(tablist, { deltaY: 80, deltaX: 0 });

    expect(tablist.scrollLeft).toBe(80);
  });
});
