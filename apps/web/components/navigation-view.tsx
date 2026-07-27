"use client";

import { Copy, ExternalLink, Pin, Search, X } from "lucide-react";
import { type CSSProperties, useMemo, useState } from "react";
import { toast } from "sonner";

import { filterCategories } from "@/lib/search";
import { API_URL } from "@/lib/api";
import { faviconUrl } from "@/lib/navigation";
import { normalizeLayoutConfig } from "@/lib/personalization";
import type { Site } from "@/lib/types";

export function NavigationView({ site, preview = false }: { site: Site; preview?: boolean }) {
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const categories = useMemo(
    () => filterCategories(site.categories, query, categoryId),
    [site.categories, query, categoryId],
  );
  const visibleCount = categories.reduce((total, category) => total + category.links.length, 0);
  const totalCount = site.categories.reduce((total, category) => total + category.links.length, 0);
  const layout = normalizeLayoutConfig(site.layout_config);
  const appearance = {
    "--site-accent": layout.accent_color,
    "--nav-columns": layout.columns,
  } as CSSProperties;

  async function copyLink(url: string) {
    await navigator.clipboard.writeText(url);
    toast.success("链接已复制");
  }

  function trackClick(linkId: string) {
    if (preview) return;
    void fetch(`${API_URL}/api/v1/public/sites/${site.public_slug}/links/${linkId}/click`, {
      method: "POST",
      credentials: "include",
      keepalive: true,
    });
  }

  return (
    <section
      className={`nav-view theme-${site.theme} canvas-${layout.canvas_style} cards-${layout.card_style} density-${layout.density} width-${layout.content_width} header-${layout.header_alignment} ${preview ? "nav-preview" : ""}`}
      style={appearance}
    >
      <div className="nav-inner">
        <header className="nav-hero">
          <div className="nav-title-row">
            <div className="site-icon" aria-hidden="true">{site.icon}</div>
            <div className="site-heading">
              <span className="workspace-kicker">共享工作台</span>
              <h1>{site.name}</h1>
              {site.description && <p>{site.description}</p>}
            </div>
          </div>
          <div className="nav-meta" aria-label="工作台摘要">
            <strong>{totalCount}</strong>
            <span>个常用入口</span>
            <i aria-hidden="true" />
            <strong>{site.categories.length}</strong>
            <span>个分组</span>
          </div>
        </header>

        {site.display_config.show_search !== false && (
          <div className="search-wrap">
            <Search size={19} aria-hidden="true" />
            <input className="search-input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索名称、标签或域名" aria-label="搜索导航链接" />
            {query && <button className="clear-search" onClick={() => setQuery("")} title="清除搜索" aria-label="清除搜索"><X size={16} /></button>}
            {query && <span className="result-count">{visibleCount} 项</span>}
          </div>
        )}

        {site.categories.length > 1 && (
          <div className="category-tabs" role="tablist" aria-label="分类筛选">
            <button className={!categoryId ? "active" : ""} onClick={() => setCategoryId(null)}>全部</button>
            {site.categories.map((category) => (
              <button key={category.id} className={categoryId === category.id ? "active" : ""} onClick={() => setCategoryId(category.id)}><span aria-hidden="true">{category.icon}</span>{category.name}</button>
            ))}
          </div>
        )}

        <div className="category-list">
          {categories.map((category) => (
            <section className="nav-category" key={category.id}>
              <div className="category-heading">
                <span className="category-icon" aria-hidden="true">{category.icon}</span>
                <div><h2>{category.name}</h2>{category.description && <p>{category.description}</p>}</div>
                <span className="category-count">{category.links.length}</span>
              </div>
              <div className="link-grid">
                {category.links.map((link) => (
                  <article className="link-card" key={link.id}>
                    <a href={preview ? undefined : link.url} target={link.open_mode === "new" ? "_blank" : "_self"} rel="noopener noreferrer" onClick={(event) => { if (preview) event.preventDefault(); else trackClick(link.id); }}>
                      <LinkIcon url={link.url} fallback={link.icon} />
                      <span className="link-content">
                        <span className="link-name">{link.name}{link.is_pinned && <Pin size={12} />}</span>
                        {site.display_config.show_descriptions !== false && link.description && <span className="link-description">{link.description}</span>}
                        {site.display_config.show_tags !== false && link.tags.length > 0 && <span className="link-tags">{link.tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}</span>}
                      </span>
                      <ExternalLink className="link-arrow" size={16} aria-hidden="true" />
                    </a>
                    {!preview && <button className="copy-link" onClick={() => copyLink(link.url)} title="复制链接" aria-label={`复制 ${link.name} 链接`}><Copy size={15} /></button>}
                  </article>
                ))}
              </div>
            </section>
          ))}
          {visibleCount === 0 && <div className="empty-search"><Search size={24} /><p>没有找到匹配的链接</p></div>}
        </div>

        <footer className="nav-footer">
          {site.display_config.show_updated_at !== false && <span>更新于 {new Date(site.updated_at).toLocaleDateString("zh-CN")}</span>}
          {site.display_config.show_visit_count && <span>{site.visit_count} 次访问</span>}
          <span className="powered-by">TeamNav</span>
          {!preview && <a href={`/report/${site.public_slug}`}>举报</a>}
        </footer>
      </div>
    </section>
  );
}

function LinkIcon({ url, fallback }: { url: string; fallback: string }) {
  const source = faviconUrl(url);
  const [failed, setFailed] = useState(false);
  // Dynamic user origins cannot be declared in a Next Image hostname allowlist.
  // eslint-disable-next-line @next/next/no-img-element
  const image = <img src={source ?? ""} alt="" onError={() => setFailed(true)} />;
  return (
    <span className="link-icon" aria-hidden="true">
      {source && !failed ? image : fallback}
    </span>
  );
}
