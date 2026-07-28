"use client";

import { useRef, useState, type PointerEvent, type WheelEvent } from "react";

type CategoryTab = { id: string; icon: string; name: string };

type Props = {
  categories: CategoryTab[];
  activeId: string | null;
  allLabel: string;
  ariaLabel: string;
  onSelect: (id: string | null) => void;
};

type DragState = {
  pointerId: number;
  startX: number;
  startScrollLeft: number;
  captured: boolean;
};

export function CategoryTabs({ categories, activeId, allLabel, ariaLabel, onSelect }: Props) {
  const drag = useRef<DragState | null>(null);
  const dragged = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
    if ((event.pointerType && event.pointerType !== "mouse") || event.button !== 0) return;
    drag.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startScrollLeft: event.currentTarget.scrollLeft,
      captured: false,
    };
  }

  function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    const distance = event.clientX - drag.current.startX;
    if (Math.abs(distance) > 5) {
      dragged.current = true;
      setIsDragging(true);
      if (!drag.current.captured) {
        event.currentTarget.setPointerCapture?.(event.pointerId);
        drag.current.captured = true;
      }
    }
    event.currentTarget.scrollLeft = drag.current.startScrollLeft - distance;
  }

  function handlePointerEnd(event: PointerEvent<HTMLDivElement>) {
    if (!drag.current || drag.current.pointerId !== event.pointerId) return;
    const captured = drag.current.captured;
    drag.current = null;
    setIsDragging(false);
    if (captured) event.currentTarget.releasePointerCapture?.(event.pointerId);
    window.setTimeout(() => {
      dragged.current = false;
    }, 0);
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return;
    event.preventDefault();
    event.currentTarget.scrollLeft += event.deltaY;
  }

  function select(id: string | null) {
    if (!dragged.current) onSelect(id);
  }

  return (
    <div
      className={`category-tabs ${isDragging ? "is-scrolling" : ""}`}
      role="tablist"
      aria-label={ariaLabel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerEnd}
      onPointerCancel={handlePointerEnd}
      onWheel={handleWheel}
    >
      <button role="tab" aria-selected={!activeId} className={!activeId ? "active" : ""} onClick={() => select(null)}>{allLabel}</button>
      {categories.map((category) => (
        <button role="tab" aria-selected={activeId === category.id} key={category.id} className={activeId === category.id ? "active" : ""} onClick={() => select(category.id)}><span aria-hidden="true">{category.icon}</span>{category.name}</button>
      ))}
    </div>
  );
}
