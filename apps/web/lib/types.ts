export type NavLink = {
  id: string;
  category_id: string;
  name: string;
  url: string;
  description: string | null;
  icon: string;
  tags: string[];
  sort_order: number;
  is_pinned: boolean;
  is_enabled: boolean;
  open_mode: "new" | "same";
  health_status: "unchecked" | "healthy" | "warning" | "broken" | "blocked";
  health_status_code: number | null;
  health_error: string | null;
  health_checked_at: string | null;
  health_consecutive_failures: number;
};

export type Category = {
  id: string;
  name: string;
  description: string | null;
  icon: string;
  sort_order: number;
  is_visible: boolean;
  links: NavLink[];
};

export type LayoutConfig = {
  accent_color: string;
  canvas_style: "clean" | "soft" | "contrast";
  card_style: "solid" | "outline" | "minimal";
  content_width: "compact" | "standard" | "wide";
  columns: 2 | 3 | 4;
  density: "comfortable" | "compact";
  header_alignment: "left" | "center";
  wallpaper_url: string | null;
  wallpaper_fit: "cover" | "contain" | "tile";
  wallpaper_position: "top" | "center" | "bottom";
  wallpaper_overlay: number;
};

export type Site = {
  public_slug: string;
  name: string;
  description: string | null;
  icon: string;
  theme: "light" | "dark" | "system";
  allow_indexing: boolean;
  password_protected: boolean;
  layout_config: LayoutConfig;
  display_config: {
    show_search?: boolean;
    show_updated_at?: boolean;
    show_visit_count?: boolean;
    show_descriptions?: boolean;
    show_tags?: boolean;
  };
  maintenance_config: {
    link_check_enabled: boolean;
    check_interval_hours: number;
  };
  visit_count: number;
  updated_at: string;
  categories: Category[];
};

export type CreateResult = {
  site: { public_slug: string; name: string };
  public_url: string;
  manage_url: string;
  recovery_payload: { version: number; public_slug: string; edit_key: string };
};
