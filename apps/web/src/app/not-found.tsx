import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <h2 className="text-3xl font-bold">404</h2>
      <p>Halaman tidak ditemukan</p>
      <Link href="/home" className="text-primary underline">
        Kembali ke beranda
      </Link>
    </main>
  );
}
