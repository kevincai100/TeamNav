"use client";

import { ChevronDown } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";

import { useI18n } from "./locale-provider";

export const CATEGORY_ICON_OPTIONS = [
  "◎", "◉", "○", "⊙", "◇", "◈",
  "□", "▦", "△", "▽", "✦", "✧",
  "※", "⌘", "⌁", "∞", "≡", "∷",
] as const;

type CategoryIconPickerProps = {
  value: string;
  label: string;
  onChange: (value: string) => void;
};

export function CategoryIconPicker({ value, label, onChange }: CategoryIconPickerProps) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const dialogId = useId();

  useEffect(() => {
    if (!open) return;
    const closeOnOutsidePress = (event: PointerEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOnOutsidePress);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutsidePress);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  const selectIcon = (icon: string) => {
    onChange(icon);
    setOpen(false);
    triggerRef.current?.focus();
  };

  return <div className="category-icon-picker" ref={rootRef}>
    <button
      ref={triggerRef}
      type="button"
      className="category-icon-trigger"
      aria-label={label}
      aria-controls={open ? dialogId : undefined}
      aria-expanded={open}
      aria-haspopup="dialog"
      onClick={() => setOpen((current) => !current)}
    >
      <span className="category-icon-value">{value || "·"}</span>
      <ChevronDown size={11} aria-hidden="true" />
    </button>
    {open && <div id={dialogId} className="category-icon-popover" role="dialog" aria-label={t("选择分类图标")}>
      <div className="category-symbol-grid" role="group" aria-label={t("选择分类图标")}>
        {CATEGORY_ICON_OPTIONS.map((icon) => <button
          key={icon}
          type="button"
          className={icon === value ? "active" : ""}
          aria-label={t("使用 {icon} 图标", { icon })}
          aria-pressed={icon === value}
          onClick={() => selectIcon(icon)}
        >{icon}</button>)}
      </div>
      <label className="category-icon-custom">
        <span>{t("自定义图标")}</span>
        <input
          aria-label={t("自定义图标")}
          value={value}
          onChange={(event) => onChange(Array.from(event.target.value).slice(0, 8).join(""))}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              setOpen(false);
              triggerRef.current?.focus();
            }
          }}
        />
      </label>
    </div>}
  </div>;
}
