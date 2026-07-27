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
import { GripVertical, Pencil, Save, Trash2 } from "lucide-react";

import type { Category, NavLink } from "@/lib/types";

type Props = {
  categories: Category[];
  patchCategory: (id: string, patch: Partial<Category>) => void;
  updateCategory: (category: Category) => void;
  removeCategory: (category: Category) => void;
  editLink: (link: NavLink) => void;
  removeLink: (link: NavLink) => void;
  reorderCategories: (activeId: string, overId: string) => void;
  reorderLinks: (category: Category, activeId: string, overId: string) => void;
};

export function SortableEditor(props: Props) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const onEnd = (event: DragEndEvent) => {
    if (event.over && event.active.id !== event.over.id) {
      props.reorderCategories(String(event.active.id), String(event.over.id));
    }
  };
  return <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onEnd}>
    <SortableContext items={props.categories.map((item) => item.id)} strategy={verticalListSortingStrategy}>
      <div className="manage-categories">{props.categories.map((category) => <SortableCategory key={category.id} category={category} {...props} />)}</div>
    </SortableContext>
  </DndContext>;
}

function SortableCategory({ category, ...props }: Omit<Props, "categories"> & { category: Category }) {
  const sortable = useSortable({ id: category.id });
  const style = { transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition };
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  const onLinkEnd = (event: DragEndEvent) => {
    if (event.over && event.active.id !== event.over.id) props.reorderLinks(category, String(event.active.id), String(event.over.id));
  };
  return <article ref={sortable.setNodeRef} style={style} className={`manage-category ${sortable.isDragging ? "is-dragging" : ""}`} data-testid={`category-${category.id}`}>
    <div className="manage-category-head">
      <button className="drag-handle" title="拖拽分类排序" aria-label={`拖拽 ${category.name} 分类`} {...sortable.attributes} {...sortable.listeners}><GripVertical size={17} /></button>
      <input className="category-icon-input" value={category.icon} onChange={(event) => props.patchCategory(category.id, { icon: event.target.value })} />
      <input className="category-name-input" value={category.name} onChange={(event) => props.patchCategory(category.id, { name: event.target.value })} />
      <button className="icon-button" title="保存分类" onClick={() => props.updateCategory(category)}><Save size={15} /></button>
      <button className="icon-button danger-icon" title="删除分类" onClick={() => props.removeCategory(category)}><Trash2 size={15} /></button>
    </div>
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onLinkEnd}>
      <SortableContext items={category.links.map((item) => item.id)} strategy={verticalListSortingStrategy}>
        <div className="manage-links">{category.links.map((link) => <SortableLink key={link.id} link={link} editLink={props.editLink} removeLink={props.removeLink} />)}{category.links.length === 0 && <p className="empty-inline">这个分类还没有链接</p>}</div>
      </SortableContext>
    </DndContext>
  </article>;
}

function SortableLink({ link, editLink, removeLink }: { link: NavLink; editLink: (link: NavLink) => void; removeLink: (link: NavLink) => void }) {
  const sortable = useSortable({ id: link.id });
  const style = { transform: CSS.Transform.toString(sortable.transform), transition: sortable.transition };
  return <div ref={sortable.setNodeRef} style={style} className={`manage-link ${sortable.isDragging ? "is-dragging" : ""}`} data-testid={`link-${link.id}`}>
    <button className="drag-handle" title="拖拽链接排序" aria-label={`拖拽 ${link.name} 链接`} {...sortable.attributes} {...sortable.listeners}><GripVertical size={15} /></button>
    <span className="mini-icon">{link.icon}</span><div><strong>{link.name}</strong><small>{link.url}</small></div>
    <button className="icon-button" title="编辑" onClick={() => editLink(link)}><Pencil size={14} /></button><button className="icon-button danger-icon" title="删除" onClick={() => removeLink(link)}><Trash2 size={14} /></button>
  </div>;
}
