import { SearchX } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';

export default function NotFoundPage() {
  return (
    <main className="site-section">
      <div className="site-container">
        <EmptyState
          icon={<SearchX size={28} />}
          title="404 — Halaman Tidak Ditemukan"
          description="Halaman yang kamu cari tidak tersedia atau telah dipindahkan."
        />
        <div className="not-found-actions">
          <Button href="/home">Kembali ke Beranda</Button>
          <Button href="/services" variant="outline">
            Lihat Layanan Kami
          </Button>
        </div>
      </div>
    </main>
  );
}
