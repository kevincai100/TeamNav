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

export type Site = {
  public_slug: string;
  name: string;
  description: string | null;
  icon: string;
  theme: "light" | "dark" | "system";
  allow_indexing: boolean;
  password_protected: boolean;
  display_config: {
    show_search?: boolean;
    show_updated_at?: boolean;
    show_visit_count?: boolean;
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
