import type { Metadata } from "next";

import { PublicSiteClient } from "./public-site-client";

const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  try {
    const response = await fetch(`${apiUrl}/api/v1/public/sites/${slug}/metadata`, { cache: "no-store" });
    if (!response.ok) throw new Error("metadata unavailable");
    const data = await response.json() as { name: string; allow_indexing: boolean };
    return {
      title: `${data.name} · TeamNav`,
      robots: data.allow_indexing ? { index: true, follow: true } : { index: false, follow: false },
    };
  } catch {
    return { title: "TeamNav", robots: { index: false, follow: false } };
  }
}

export default async function PublicSitePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <PublicSiteClient slug={slug} />;
}
