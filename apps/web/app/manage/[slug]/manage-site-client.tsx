"use client";

import {
  AlignCenter, AlignLeft, BarChart3, Copy, CopyPlus, Database, Download, Eye,
  FileUp, KeyRound, LayoutGrid, Link2, Monitor, Moon, Palette, Plus, RotateCw,
  Save, Settings2, ShieldCheck, Sun, Trash2, UserPlus,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { NavigationView } from "@/components/navigation-view";
import { SortableEditor } from "@/components/sortable-editor";
import { API_URL, api, ApiError } from "@/lib/api";
import { reorderItems } from "@/lib/navigation";
import { ACCENT_PRESETS } from "@/lib/personalization";
import type { Category, NavLink, Site } from "@/lib/types";

type SessionResponse = { site: Site; csrf_token: string };
type Stats = { totals: { page_views: number; link_clicks: number }; daily: { date: string; page_views: number; link_clicks: number }[] };

export function ManageSiteClient({ slug }: { slug: string }) {
  const [site, setSite] = useState<Site | null>(null);
  const [csrf, setCsrf] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "denied">("loading");
  const [mobileView, setMobileView] = useState<"edit" | "preview">("edit");
  const [editorTab, setEditorTab] = useState<"content" | "appearance" | "settings">("content");
  const [categoryName, setCategoryName] = useState("");
  const [categoryIcon, setCategoryIcon] = useState("📁");
  const [linkDraft, setLinkDraft] = useState({ category_id: "", name: "", url: "", description: "", icon: "🔗", tags: "" });
  const [editingLink, setEditingLink] = useState<NavLink | null>(null);
  const [batch, setBatch] = useState("");
  const [rotatedUrl, setRotatedUrl] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [passwordChanged, setPasswordChanged] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [cloneUrl, setCloneUrl] = useState("");

  const loadSite = useCallback(async () => {
    const data = await api<Site>(`/api/v1/manage/sites/${slug}`);
    setSite(data);
    setLinkDraft((draft) => ({ ...draft, category_id: draft.category_id || data.categories[0]?.id || "" }));
    return data;
  }, [slug]);

  useEffect(() => {
    async function connect() {
      const url = new URL(window.location.href);
      const key = url.searchParams.get("key");
      try {
        if (key) {
          const result = await api<SessionResponse>(`/api/v1/manage/sites/${slug}/session`, { method: "POST", body: JSON.stringify({ edit_key: key }) });
          sessionStorage.setItem(`teamnav_csrf_${slug}`, result.csrf_token);
          setCsrf(result.csrf_token);
          url.searchParams.delete("key");
          window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
        } else {
          setCsrf(sessionStorage.getItem(`teamnav_csrf_${slug}`) ?? sessionStorage.getItem("teamnav_account_csrf") ?? "");
        }
        await loadSite();
        setStats(await api<Stats>(`/api/v1/manage/sites/${slug}/stats`));
        setStatus("ready");
      } catch { setStatus("denied"); }
    }
    void connect();
  }, [loadSite, slug]);

  async function write<T>(path: string, method: string, body?: unknown): Promise<T> {
    if (!csrf) throw new ApiError(403, "CSRF_MISSING");
    return api<T>(path, { method, headers: { "X-CSRF-Token": csrf }, body: body === undefined ? undefined : JSON.stringify(body) });
  }

  async function saveSettings() {
    if (!site) return;
    try {
      const payload: Record<string, unknown> = {
        name: site.name, description: site.description, icon: site.icon, theme: site.theme,
        allow_indexing: site.allow_indexing,
        show_search: site.display_config.show_search,
        show_updated_at: site.display_config.show_updated_at,
        show_visit_count: site.display_config.show_visit_count,
        show_descriptions: site.display_config.show_descriptions,
        show_tags: site.display_config.show_tags,
        layout_config: site.layout_config,
      };
      if (passwordChanged) payload.access_password = newPassword;
      const updated = await write<Site>(`/api/v1/manage/sites/${slug}`, "PATCH", payload);
      setSite(updated); setPasswordChanged(false); setNewPassword(""); toast.success("站点设置已保存");
    } catch { toast.error("保存失败，请重新打开私密编辑链接"); }
  }

  async function addCategory(event: React.FormEvent) {
    event.preventDefault();
    try {
      await write(`/api/v1/manage/sites/${slug}/categories`, "POST", { name: categoryName, icon: categoryIcon });
      setCategoryName(""); await loadSite(); toast.success("分类已添加");
    } catch { toast.error("分类添加失败"); }
  }

  async function updateCategory(category: Category) {
    try { await write(`/api/v1/manage/sites/${slug}/categories/${category.id}`, "PATCH", { name: category.name, description: category.description, icon: category.icon, is_visible: category.is_visible }); await loadSite(); toast.success("分类已更新"); }
    catch { toast.error("分类更新失败"); }
  }

  async function removeCategory(category: Category) {
    if (!window.confirm(`删除“${category.name}”及其中全部链接？`)) return;
    try { await write(`/api/v1/manage/sites/${slug}/categories/${category.id}`, "DELETE"); await loadSite(); }
    catch { toast.error("分类删除失败"); }
  }

  async function reorderCategories(activeId: string, overId: string) {
    if (!site) return;
    const next = reorderItems(site.categories, activeId, overId);
    setSite({ ...site, categories: next });
    try { await write(`/api/v1/manage/sites/${slug}/categories/reorder`, "PUT", next.map(({ id, sort_order }) => ({ id, sort_order }))); }
    catch { await loadSite(); toast.error("排序保存失败"); }
  }

  async function addLink(event: React.FormEvent) {
    event.preventDefault();
    try {
      await write(`/api/v1/manage/sites/${slug}/links`, "POST", { ...linkDraft, tags: linkDraft.tags.split(",").map((tag) => tag.trim()).filter(Boolean) });
      setLinkDraft((draft) => ({ ...draft, name: "", url: "", description: "", tags: "" })); await loadSite(); toast.success("链接已添加");
    } catch (error) { toast.error(error instanceof ApiError && error.status === 422 ? "请输入 http、https、mailto 或 tel 链接" : "链接添加失败"); }
  }

  async function saveLink(event: React.FormEvent) {
    event.preventDefault(); if (!editingLink) return;
    try { await write(`/api/v1/manage/sites/${slug}/links/${editingLink.id}`, "PATCH", editingLink); setEditingLink(null); await loadSite(); toast.success("链接已更新"); }
    catch { toast.error("链接更新失败"); }
  }

  async function removeLink(link: NavLink) {
    if (!window.confirm(`删除“${link.name}”？`)) return;
    try { await write(`/api/v1/manage/sites/${slug}/links/${link.id}`, "DELETE"); await loadSite(); }
    catch { toast.error("链接删除失败"); }
  }

  async function reorderLinks(category: Category, activeId: string, overId: string) {
    if (!site) return;
    const links = reorderItems(category.links, activeId, overId);
    setSite({ ...site, categories: site.categories.map((item) => item.id === category.id ? { ...item, links } : item) });
    try { await write(`/api/v1/manage/sites/${slug}/links/reorder`, "PUT", links.map(({ id, sort_order }) => ({ id, sort_order }))); }
    catch { await loadSite(); toast.error("排序保存失败"); }
  }

  async function batchAdd() {
    if (!linkDraft.category_id || !batch.trim()) return;
    try { await write(`/api/v1/manage/sites/${slug}/links/batch`, "POST", { category_id: linkDraft.category_id, lines: batch }); setBatch(""); await loadSite(); toast.success("批量链接已添加"); }
    catch { toast.error("请检查每行的 URL 格式"); }
  }

  async function exportSite() {
    const data = await api<Record<string, unknown>>(`/api/v1/manage/sites/${slug}/export`);
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `teamnav-${slug}.json`; anchor.click(); URL.revokeObjectURL(url);
  }

  async function exportBookmarks() {
    const response = await fetch(`${API_URL}/api/v1/manage/sites/${slug}/bookmarks/export`, { credentials: "include" });
    if (!response.ok) return toast.error("书签导出失败");
    const url = URL.createObjectURL(await response.blob());
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `teamnav-${slug}-bookmarks.html`; anchor.click(); URL.revokeObjectURL(url);
  }

  async function importBookmarks(file: File) {
    try {
      const result = await write<{ imported_categories: number; imported_links: number }>(`/api/v1/manage/sites/${slug}/bookmarks/import`, "POST", { mode: "merge", html: await file.text() });
      await loadSite(); toast.success(`已导入 ${result.imported_links} 个书签`);
    } catch { toast.error("书签文件无效"); }
  }

  async function cloneSite() {
    if (!site || !window.confirm("克隆将创建一个独立站点，并生成新的私密编辑链接。继续吗？")) return;
    try { const result = await write<{ manage_url: string }>(`/api/v1/manage/sites/${slug}/clone`, "POST", { name: `${site.name} 副本` }); setCloneUrl(result.manage_url); }
    catch { toast.error("站点克隆失败"); }
  }

  async function claimToAccount() {
    try {
      await write(`/api/v1/manage/sites/${slug}/claim`, "POST");
      toast.success("已同步到个人账号");
    } catch (error) {
      toast.error(error instanceof ApiError && error.status === 401 ? "请先登录个人账号" : "同步失败");
    }
  }

  async function loadStats() {
    try { setStats(await api<Stats>(`/api/v1/manage/sites/${slug}/stats`)); }
    catch { setStats(null); }
  }

  async function importSite(file: File) {
    try { const data = JSON.parse(await file.text()); if (!window.confirm("覆盖导入会删除当前分类和链接，继续吗？")) return; await write(`/api/v1/manage/sites/${slug}/import`, "POST", { mode: "replace", data }); await loadSite(); toast.success("导入完成"); }
    catch { toast.error("导入文件无效"); }
  }

  async function rotateKey() {
    if (!window.confirm("轮换后，旧编辑链接和当前管理会话都会立即失效。继续吗？")) return;
    try { const result = await write<{ manage_url: string }>(`/api/v1/manage/sites/${slug}/rotate-edit-key`, "POST"); setRotatedUrl(result.manage_url); sessionStorage.removeItem(`teamnav_csrf_${slug}`); }
    catch { toast.error("轮换失败"); }
  }

  async function deleteSite() {
    if (!site) return;
    const name = window.prompt(`请输入站点名称“${site.name}”确认删除`);
    if (name !== site.name || !window.confirm("站点删除后将立即不可访问，且无法恢复。确认删除？")) return;
    try { await write(`/api/v1/manage/sites/${slug}`, "DELETE", { confirm_name: name }); window.location.href = "/"; }
    catch { toast.error("删除失败"); }
  }

  function patchCategory(id: string, patch: Partial<Category>) {
    if (!site) return; setSite({ ...site, categories: site.categories.map((category) => category.id === id ? { ...category, ...patch } : category) });
  }

  function patchLayout(patch: Partial<Site["layout_config"]>) {
    if (!site) return;
    setSite({ ...site, layout_config: { ...site.layout_config, ...patch } });
  }

  if (status === "loading") return <main className="loading"><div className="spinner" /></main>;
  if (status === "denied" || !site) return <main className="error-state"><KeyRound size={34} /><h1>无法进入管理模式</h1><p className="muted">请使用创建时保存的私密编辑链接重新打开。</p></main>;

  return (
    <main className="manage-page">
      <div className="manage-toolbar">
        <div><span className="eyebrow">管理模式</span><h1>{site.name}</h1></div>
        <div className="manage-toolbar-actions"><button className="button secondary" onClick={() => navigator.clipboard.writeText(`${window.location.origin}/s/${slug}`)}><Copy size={16} /> 公开链接</button><a className="button" href={`/s/${slug}`} target="_blank" rel="noopener noreferrer"><Eye size={16} /> 打开公开页</a></div>
      </div>

      <div className="mobile-view-switch" role="tablist"><button className={mobileView === "edit" ? "active" : ""} onClick={() => setMobileView("edit")}><Settings2 size={15} /> 编辑</button><button className={mobileView === "preview" ? "active" : ""} onClick={() => setMobileView("preview")}><Eye size={15} /> 预览</button></div>

      <div className="manage-layout">
        <section className={`manage-editor ${mobileView === "preview" ? "mobile-hidden" : ""}`}>
          {!csrf && <div className="notice">当前标签页缺少写入凭证。请用私密编辑链接重新打开后再修改。</div>}
          <nav className="editor-tabs" aria-label="编辑区域">
            <button className={editorTab === "content" ? "active" : ""} onClick={() => setEditorTab("content")}><LayoutGrid size={16} /> 内容</button>
            <button className={editorTab === "appearance" ? "active" : ""} onClick={() => setEditorTab("appearance")}><Palette size={16} /> 外观</button>
            <button className={editorTab === "settings" ? "active" : ""} onClick={() => setEditorTab("settings")}><Settings2 size={16} /> 设置</button>
          </nav>

          {editorTab === "appearance" && <>
            <section className="editor-section">
              <div className="section-title"><span><Palette size={17} /> 品牌与外观</span><span>实时预览</span></div>
              <div className="editor-content appearance-editor">
                <div className="form-grid">
                  <div className="field span-2"><label>工作台名称</label><input value={site.name} onChange={(event) => setSite({ ...site, name: event.target.value })} /></div>
                  <div className="field span-2"><label>一句话描述</label><textarea value={site.description ?? ""} onChange={(event) => setSite({ ...site, description: event.target.value })} /></div>
                  <div className="field"><label>标识</label><input value={site.icon} onChange={(event) => setSite({ ...site, icon: event.target.value })} /></div>
                </div>

                <fieldset className="appearance-group">
                  <legend>明暗主题</legend>
                  <div className="choice-grid three">
                    <button className={site.theme === "light" ? "active" : ""} onClick={() => setSite({ ...site, theme: "light" })}><Sun size={17} /><span>浅色</span></button>
                    <button className={site.theme === "dark" ? "active" : ""} onClick={() => setSite({ ...site, theme: "dark" })}><Moon size={17} /><span>深色</span></button>
                    <button className={site.theme === "system" ? "active" : ""} onClick={() => setSite({ ...site, theme: "system" })}><Monitor size={17} /><span>跟随系统</span></button>
                  </div>
                </fieldset>

                <fieldset className="appearance-group">
                  <legend>品牌色</legend>
                  <div className="color-row">
                    {ACCENT_PRESETS.map((color) => <button key={color} className={`color-swatch ${site.layout_config.accent_color.toUpperCase() === color ? "active" : ""}`} style={{ backgroundColor: color }} onClick={() => patchLayout({ accent_color: color })} title={color} aria-label={`选择品牌色 ${color}`} />)}
                    <label className="custom-color" title="自定义品牌色"><input type="color" value={site.layout_config.accent_color} onChange={(event) => patchLayout({ accent_color: event.target.value.toUpperCase() })} /><Palette size={16} /></label>
                  </div>
                </fieldset>

                <fieldset className="appearance-group">
                  <legend>页面背景</legend>
                  <div className="choice-grid three">
                    {([['clean', '纯净'], ['soft', '柔和'], ['contrast', '对比']] as const).map(([value, label]) => <button key={value} className={site.layout_config.canvas_style === value ? "active" : ""} onClick={() => patchLayout({ canvas_style: value })}><span className={`canvas-sample ${value}`} />{label}</button>)}
                  </div>
                </fieldset>

                <fieldset className="appearance-group">
                  <legend>卡片风格</legend>
                  <div className="choice-grid three">
                    {([['solid', '实体'], ['outline', '描边'], ['minimal', '极简']] as const).map(([value, label]) => <button key={value} className={site.layout_config.card_style === value ? "active" : ""} onClick={() => patchLayout({ card_style: value })}><span className={`card-sample ${value}`} />{label}</button>)}
                  </div>
                </fieldset>

                <div className="appearance-pair">
                  <fieldset className="appearance-group">
                    <legend>每行卡片</legend>
                    <div className="segmented-control">{([2, 3, 4] as const).map((columns) => <button key={columns} className={site.layout_config.columns === columns ? "active" : ""} onClick={() => patchLayout({ columns })}>{columns}</button>)}</div>
                  </fieldset>
                  <fieldset className="appearance-group">
                    <legend>内容密度</legend>
                    <div className="segmented-control"><button className={site.layout_config.density === "comfortable" ? "active" : ""} onClick={() => patchLayout({ density: "comfortable" })}>舒适</button><button className={site.layout_config.density === "compact" ? "active" : ""} onClick={() => patchLayout({ density: "compact" })}>紧凑</button></div>
                  </fieldset>
                </div>

                <div className="appearance-pair">
                  <fieldset className="appearance-group">
                    <legend>内容宽度</legend>
                    <div className="segmented-control">{([['compact', '窄'], ['standard', '标准'], ['wide', '宽']] as const).map(([value, label]) => <button key={value} className={site.layout_config.content_width === value ? "active" : ""} onClick={() => patchLayout({ content_width: value })}>{label}</button>)}</div>
                  </fieldset>
                  <fieldset className="appearance-group">
                    <legend>标题对齐</legend>
                    <div className="segmented-control icon-segments"><button className={site.layout_config.header_alignment === "left" ? "active" : ""} onClick={() => patchLayout({ header_alignment: "left" })} title="左对齐"><AlignLeft size={16} /></button><button className={site.layout_config.header_alignment === "center" ? "active" : ""} onClick={() => patchLayout({ header_alignment: "center" })} title="居中"><AlignCenter size={16} /></button></div>
                  </fieldset>
                </div>

                <fieldset className="appearance-group">
                  <legend>页面内容</legend>
                  <div className="toggle-list">
                    <label className="toggle-field"><input type="checkbox" checked={site.display_config.show_search !== false} onChange={(event) => setSite({ ...site, display_config: { ...site.display_config, show_search: event.target.checked } })} /><span>搜索框</span></label>
                    <label className="toggle-field"><input type="checkbox" checked={site.display_config.show_descriptions !== false} onChange={(event) => setSite({ ...site, display_config: { ...site.display_config, show_descriptions: event.target.checked } })} /><span>链接描述</span></label>
                    <label className="toggle-field"><input type="checkbox" checked={site.display_config.show_tags !== false} onChange={(event) => setSite({ ...site, display_config: { ...site.display_config, show_tags: event.target.checked } })} /><span>链接标签</span></label>
                    <label className="toggle-field"><input type="checkbox" checked={site.display_config.show_updated_at !== false} onChange={(event) => setSite({ ...site, display_config: { ...site.display_config, show_updated_at: event.target.checked } })} /><span>更新时间</span></label>
                    <label className="toggle-field"><input type="checkbox" checked={site.display_config.show_visit_count === true} onChange={(event) => setSite({ ...site, display_config: { ...site.display_config, show_visit_count: event.target.checked } })} /><span>访问次数</span></label>
                  </div>
                </fieldset>
                <button className="button editor-save" onClick={saveSettings}><Save size={16} /> 保存并发布外观</button>
              </div>
            </section>
          </>}

          {editorTab === "content" && <><section className="editor-section">
            <div className="section-title"><span><Settings2 size={17} /> 分类与链接</span><span>{site.categories.length} 个分类</span></div>
            <div className="editor-content">
              <form className="quick-add" onSubmit={addCategory}><input aria-label="分类图标" value={categoryIcon} onChange={(event) => setCategoryIcon(event.target.value)} /><input aria-label="分类名称" placeholder="新分类名称" required value={categoryName} onChange={(event) => setCategoryName(event.target.value)} /><button className="icon-button" title="添加分类"><Plus size={17} /></button></form>
              <SortableEditor categories={site.categories} patchCategory={patchCategory} updateCategory={(category) => void updateCategory(category)} removeCategory={(category) => void removeCategory(category)} editLink={setEditingLink} removeLink={(link) => void removeLink(link)} reorderCategories={(active, over) => void reorderCategories(active, over)} reorderLinks={(category, active, over) => void reorderLinks(category, active, over)} />
            </div>
          </section>

          <details className="editor-section" open>
            <summary><span><Link2 size={17} /> 添加链接</span></summary>
            <form className="editor-content form-grid" data-testid="add-link-form" onSubmit={addLink}>
              <div className="field span-2"><label>所属分类</label><select required value={linkDraft.category_id} onChange={(event) => setLinkDraft({ ...linkDraft, category_id: event.target.value })}><option value="">请选择分类</option>{site.categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></div>
              <div className="field"><label>名称</label><input aria-label="链接名称" required value={linkDraft.name} onChange={(event) => setLinkDraft({ ...linkDraft, name: event.target.value })} /></div>
              <div className="field"><label>图标</label><input value={linkDraft.icon} onChange={(event) => setLinkDraft({ ...linkDraft, icon: event.target.value })} /></div>
              <div className="field span-2"><label>URL</label><input aria-label="链接 URL" required type="url" placeholder="https://" value={linkDraft.url} onChange={(event) => setLinkDraft({ ...linkDraft, url: event.target.value })} /></div>
              <div className="field"><label>描述</label><input value={linkDraft.description} onChange={(event) => setLinkDraft({ ...linkDraft, description: event.target.value })} /></div>
              <div className="field"><label>标签（逗号分隔）</label><input aria-label="链接标签" value={linkDraft.tags} onChange={(event) => setLinkDraft({ ...linkDraft, tags: event.target.value })} /></div>
              <button className="button span-2"><Plus size={16} /> 添加链接</button>
            </form>
          </details>

          <details className="editor-section">
            <summary><span><FileUp size={17} /> 批量与数据</span></summary>
            <div className="editor-content form-stack">
              <div className="field"><label>批量添加，每行“名称 | URL | 描述 | 标签1,标签2”</label><textarea value={batch} onChange={(event) => setBatch(event.target.value)} placeholder="GitHub | https://github.com | 代码托管 | 代码,常用" /></div>
              <button className="button secondary" onClick={batchAdd}>批量添加到所选分类</button>
              <div className="data-actions"><button className="button secondary" onClick={exportSite}><Download size={16} /> 导出 JSON</button><label className="button secondary"><FileUp size={16} /> 覆盖导入<input type="file" accept="application/json" hidden onChange={(event) => event.target.files?.[0] && importSite(event.target.files[0])} /></label></div>
              <div className="data-actions"><button className="button secondary" onClick={exportBookmarks}><Download size={16} /> 导出浏览器书签</button><label className="button secondary"><FileUp size={16} /> 导入书签<input type="file" accept="text/html,.html" hidden onChange={(event) => event.target.files?.[0] && void importBookmarks(event.target.files[0])} /></label></div>
            </div>
          </details>
          </>}

          {editorTab === "settings" && <><section className="editor-section">
            <div className="section-title"><span><ShieldCheck size={17} /> 访问与收录</span></div>
            <div className="editor-content form-stack">
              <label className="toggle-field"><input type="checkbox" checked={site.allow_indexing} onChange={(event) => setSite({ ...site, allow_indexing: event.target.checked })} /><span>允许搜索引擎收录</span></label>
              <div className="field"><label>公开访问密码</label><input type="password" autoComplete="new-password" value={newPassword} onChange={(event) => { setNewPassword(event.target.value); setPasswordChanged(true); }} placeholder={site.password_protected ? "已启用；输入新密码可替换" : "输入至少 6 位密码以启用"} />{passwordChanged && newPassword && newPassword.length < 6 && <span className="field-error">密码至少 6 位</span>}{site.password_protected && <button type="button" className="button ghost" onClick={() => { setNewPassword(""); setPasswordChanged(true); }}>关闭访问密码</button>}</div>
              <button className="button" disabled={passwordChanged && newPassword.length > 0 && newPassword.length < 6} onClick={saveSettings}><Save size={16} /> 保存访问设置</button>
            </div>
          </section>

          <details className="editor-section" open>
            <summary><span><BarChart3 size={17} /> 基础统计</span></summary>
            <div className="editor-content stats-panel"><div><strong>{stats?.totals.page_views ?? 0}</strong><span>页面访问</span></div><div><strong>{stats?.totals.link_clicks ?? 0}</strong><span>链接点击</span></div><button className="icon-button" title="刷新统计" onClick={() => void loadStats()}><RotateCw size={15} /></button></div>
          </details>

          <details className="editor-section danger-zone">
            <summary><span><Database size={17} /> 工作台与数据</span></summary>
            <div className="editor-content form-stack"><button className="button secondary" onClick={claimToAccount}><UserPlus size={16} /> 同步到个人账号</button><button className="button secondary" onClick={cloneSite}><CopyPlus size={16} /> 克隆站点</button><button className="button secondary" onClick={rotateKey}><RotateCw size={16} /> 轮换私密编辑链接</button><button className="button danger" onClick={deleteSite}><Trash2 size={16} /> 删除这个站点</button></div>
          </details>
          </>}
        </section>

        <aside className={`manage-preview ${mobileView === "edit" ? "mobile-hidden-preview" : ""}`}><div className="preview-label"><Eye size={15} /> 实时预览</div><NavigationView site={site} preview /></aside>
      </div>

      {editingLink && <div className="modal-backdrop" role="presentation"><form className="modal panel" onSubmit={saveLink}><div className="panel-header"><h2>编辑链接</h2><button type="button" className="icon-button" onClick={() => setEditingLink(null)}>×</button></div><div className="panel-body form-stack"><div className="field"><label>名称</label><input value={editingLink.name} onChange={(event) => setEditingLink({ ...editingLink, name: event.target.value })} /></div><div className="field"><label>URL</label><input value={editingLink.url} onChange={(event) => setEditingLink({ ...editingLink, url: event.target.value })} /></div><div className="field"><label>描述</label><textarea value={editingLink.description ?? ""} onChange={(event) => setEditingLink({ ...editingLink, description: event.target.value })} /></div><div className="field"><label>标签（可选，逗号分隔）</label><input value={editingLink.tags.join(", ")} onChange={(event) => setEditingLink({ ...editingLink, tags: event.target.value.split(",").map((tag) => tag.trim()).filter(Boolean).slice(0, 10) })} /></div><label className="toggle-field"><input type="checkbox" checked={editingLink.is_pinned} onChange={(event) => setEditingLink({ ...editingLink, is_pinned: event.target.checked })} />置顶链接</label><label className="toggle-field"><input type="checkbox" checked={editingLink.is_enabled} onChange={(event) => setEditingLink({ ...editingLink, is_enabled: event.target.checked })} />公开显示</label><button className="button"><Save size={16} /> 保存链接</button></div></form></div>}

      {rotatedUrl && <div className="modal-backdrop"><div className="modal panel"><div className="panel-header"><h2>新的私密编辑链接</h2></div><div className="panel-body form-stack"><div className="notice">旧链接已经失效。请立即保存下面的新链接。</div><code className="rotated-url">{rotatedUrl}</code><button className="button" onClick={async () => { await navigator.clipboard.writeText(rotatedUrl); window.location.href = rotatedUrl; }}><Copy size={16} /> 复制并重新进入</button></div></div></div>}
      {cloneUrl && <div className="modal-backdrop"><div className="modal panel"><div className="panel-header"><h2>克隆站点已创建</h2><button className="icon-button" onClick={() => setCloneUrl("")}>×</button></div><div className="panel-body form-stack"><div className="notice">这是克隆站点唯一可恢复的私密编辑链接，请立即保存。</div><code className="rotated-url">{cloneUrl}</code><a className="button" href={cloneUrl}><CopyPlus size={16} /> 进入克隆站点</a></div></div></div>}
    </main>
  );
}
