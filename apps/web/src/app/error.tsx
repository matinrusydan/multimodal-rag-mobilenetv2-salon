'use client';

import { RotateCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';

export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="site-section">
      <div className="site-container">
        <EmptyState
          icon={<RotateCcw size={28} />}
          title="Terjadi kesalahan tampilan."
          description="Error boundary statis ini menjaga pengalaman portfolio tetap jelas."
        />
        <div className="not-found-actions">
          <Button onClick={reset}>Coba Lagi</Button>
          <Button href="/home" variant="outline">
            Kembali ke Beranda
          </Button>
        </div>
      </div>
    </main>
  );
}
