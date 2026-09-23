import { type SalonInfo, salonInfo as fallback } from '@/data/salon-info';

/**
 * Ambil info salon dari settings publik (DB) via API, dengan fallback ke
 * data statis `salon-info.ts` bila tidak tersedia / gagal.
 *
 * Setting DB menyimpan `site` (name, tagline, address, phone, email,
 * mapEmbedUrl, operatingHours, socialLinks, stats). Field yang kosong di DB
 * akan diisi dari fallback agar tidak menampilkan data kosong.
 */
export async function getSalonInfo(): Promise<SalonInfo> {
  const baseUrl = process.env.BACKEND_URL ?? 'http://127.0.0.1:4000';
  try {
    const res = await fetch(`${baseUrl}/api/settings/public`, {
      cache: 'no-store',
    });
    if (!res.ok) return fallback;
    const body = (await res.json().catch(() => null)) as {
      data?: { site?: Partial<SalonInfo> | null };
    } | null;
    const site = body?.data?.site;
    if (!site) return fallback;

    return {
      name: site.name || fallback.name,
      tagline: site.tagline || fallback.tagline,
      address: site.address || fallback.address,
      phone: site.phone || fallback.phone,
      email: site.email || fallback.email,
      mapEmbedUrl: site.mapEmbedUrl || fallback.mapEmbedUrl,
      operatingHours:
        site.operatingHours && site.operatingHours.length > 0
          ? site.operatingHours
          : fallback.operatingHours,
      socialLinks:
        site.socialLinks && site.socialLinks.length > 0 ? site.socialLinks : fallback.socialLinks,
      stats: site.stats && site.stats.length > 0 ? site.stats : fallback.stats,
    };
  } catch {
    return fallback;
  }
}
