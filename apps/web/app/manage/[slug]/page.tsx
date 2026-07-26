import { ManageSiteClient } from "./manage-site-client";

export default async function ManageSitePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <ManageSiteClient slug={slug} />;
}
