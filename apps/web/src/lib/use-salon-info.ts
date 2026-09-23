'use client';

import { useEffect, useState } from 'react';

import { type SalonInfo, salonInfo as fallback } from '@/data/salon-info';

let cache: SalonInfo | null = null;

/**
 * Hook client: ambil info salon dari `/api/settings/public` sekali (cache modul),
 * fallback ke data statis bila gagal. Untuk komponen di client tree (footer/hero).
 */
export function useSalonInfo(): SalonInfo {
  const [info, setInfo] = useState<SalonInfo>(cache ?? fallback);

  useEffect(() => {
    if (cache) return;
    let cancelled = false;
    fetch('/api/settings/public', { cache: 'no-store' })
      .then((res) => res.json())
      .then((body: { data?: { site?: Partial<SalonInfo> | null } }) => {
        if (cancelled) return;
        const site = body?.data?.site;
        if (!site) return;
        const merged: SalonInfo = {
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
            site.socialLinks && site.socialLinks.length > 0
              ? site.socialLinks
              : fallback.socialLinks,
          stats: site.stats && site.stats.length > 0 ? site.stats : fallback.stats,
        };
        cache = merged;
        setInfo(merged);
      })
      .catch(() => {
        /* pakai fallback */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return info;
}
