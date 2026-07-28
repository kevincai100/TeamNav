"use client";

/* eslint-disable react-hooks/refs -- dnd-kit exposes callback refs and attributes through its hook result. */

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  ChevronDown,
  ChevronRight,
  ChevronsDownUp,
  ChevronsUpDown,
  GripVertical,
  Pencil,
  Save,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import { CategoryIconPicker } from "@/components/category-icon-picker";
import { isFolderCollapsed } from "@/lib/folder-collapse";
import type { Category, NavLink } from "@/lib/types";
import { useI18n } from "@/components/locale-provider";

type Props = {
  categories: Category[];
  patchCategory: (id: string, patch: Partial<Category>) => void;
  updateCategory: (category: Category) => void;
  removeCategory: (category: Category) => void;
  editLink: (link: NavLink) => void;
  removeLink: (link: NavLink) => void;
  reorderCategories: (activeId: string, overId: string) => void;
  reorderLinks: (activeId: string, targetCategoryId: string, overId?: string) => void;
};

type SortableData =
  | { type: "category"; categoryId: string }
  | { type: "link"; categoryId: string; linkId: string };

const categoryDndId = (id: string) => `category:${id}`;
const linkDndId = (id: string) => `link:${id}`;

export function SortableEditor(props: Props) {
  const { t } = useI18n();
  const [collapseOverrides, setCollapseOverrides] = useState<Map<string, boolean>>(
    () => new Map(),
  );
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const onEnd = (event: DragEndEvent) => {
    if (!event.over || event.active.id === event.over.id) return;
    const active = event.active.data.current as SortableData | undefined;
    const over = event.over.data.current as SortableData | undefined;
    if (!active || !over) return;
    if (active.type === "category") {
      props.reorderCategories(active.categoryId, over.categoryId);
      return;
    }
    props.reorderLinks(
      active.linkId,
      over.categoryId,
      over.type === "link" ? over.linkId : undefined,
    );
  };
  const categoryCollapsed = (id: string) =>
    isFolderCollapsed(collapseOverrides, id, props.categories.length);
  const allCollapsed = props.categories.length > 0
    && props.categories.every(({ id }) => categoryCollapsed(id));
  const toggleCategory = (id: string) => {
    setCollapseOverrides((current) => {
      const next = new Map(current);
      next.set(id, !isFolderCollapsed(current, id, props.categories.length));
      return next;
    });
  };
  return <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onEnd}>
    <div className="category-organizer-toolbar">
      <button
        type="button"
        className="icon-button"
        title={t(allCollapsed ? "展开全部目录" : "收起全部目录")}
        aria-label={t(allCollapsed ? "展开全部目录" : "收起全部目录")}
        onClick={() => setCollapseOverrides(new Map(
          props.categories.map(({ id }) => [id, !allCollapsed]),
        ))}
      >
        {allCollapsed ? <ChevronsUpDown size={16} /> : <ChevronsDownUp size={16} />}
      </button>
    </div>
    <SortableContext items={props.categories.map((item) => categoryDndId(item.id))} strategy={verticalListSortingStrategy}>
      <div className="manage-categories">{props.categories.map((category) => <SortableCategory key={category.id} category={category} collapsed={categoryCollapsed(category.id)} toggleCategory={toggleCategory} {...props} />)}</div>
    </SortableContext>
  </DndContext>;
}

function SortableCategory({ category, collapsed, toggleCategory, ...props }: Omit<Props, "categories"> & { category: Category; collapsed: boolean; toggleCategory: (id: string) => void }) {
  const { t } = useI18n();
  const sortable = useSortable({
    id: categoryDndId(category.id),
    data: { type: "category", categoryId: category.id } satisfies SortableData,
  });
  const style = { transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition };
  return <article ref={sortable.setNodeRef} style={style} className={`manage-category ${sortable.isDragging ? "is-dragging" : ""}`} data-testid={`category-${category.id}`}>
    <div className="manage-category-head">
      <button type="button" className="category-toggle" title={t(collapsed ? "展开目录" : "收起目录")} aria-label={t(collapsed ? "展开 {name} 目录" : "收起 {name} 目录", { name: category.name })} onClick={() => toggleCategory(category.id)}>{collapsed ? <ChevronRight size={17} /> : <ChevronDown size={17} />}</button>
      <button className="drag-handle" title={t("拖拽分类排序")} aria-label={t("拖拽 {name} 分类", { name: category.name })} {...sortable.attributes} {...sortable.listeners}><GripVertical size={17} /></button>
      <CategoryIconPicker value={category.icon} label={t("{name} 分类图标", { name: category.name })} onChange={(icon) => props.patchCategory(category.id, { icon })} />
      <input className="category-name-input" value={category.name} onChange={(event) => props.patchCategory(category.id, { name: event.target.value })} />
      <button className="icon-button" title={t("保存分类")} onClick={() => props.updateCategory(category)}><Save size={15} /></button>
      <button className="icon-button danger-icon" title={t("删除分类")} onClick={() => props.removeCategory(category)}><Trash2 size={15} /></button>
    </div>
    {!collapsed && <SortableContext items={category.links.map((item) => linkDndId(item.id))} strategy={verticalListSortingStrategy}>
      <div className="manage-links">{category.links.map((link) => <SortableLink key={link.id} link={link} editLink={props.editLink} removeLink={props.removeLink} />)}{category.links.length === 0 && <p className="empty-inline">{t("这个分类还没有链接")}</p>}</div>
    </SortableContext>}
  </article>;
}

function SortableLink({ link, editLink, removeLink }: { link: NavLink; editLink: (link: NavLink) => void; removeLink: (link: NavLink) => void }) {
  const { t } = useI18n();
  const sortable = useSortable({
    id: linkDndId(link.id),
    data: { type: "link", categoryId: link.category_id, linkId: link.id } satisfies SortableData,
  });
  const style = { transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition };
  return <div ref={sortable.setNodeRef} style={style} className={`manage-link ${sortable.isDragging ? "is-dragging" : ""}`} data-testid={`link-${link.id}`}>
    <button className="drag-handle" title={t("拖拽链接排序")} aria-label={t("拖拽 {name} 链接", { name: link.name })} {...sortable.attributes} {...sortable.listeners}><GripVertical size={15} /></button>
    <span className="mini-icon">{link.icon}</span><div><strong>{link.name}</strong><small>{link.url}</small></div>
    <button className="icon-button" title={t("编辑")} onClick={() => editLink(link)}><Pencil size={14} /></button><button className="icon-button danger-icon" title={t("删除")} onClick={() => removeLink(link)}><Trash2 size={14} /></button>
  </div>;
}
