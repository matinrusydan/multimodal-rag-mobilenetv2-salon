export default function HomePage() {
  return (
    <main className="p-6">
      <h1 className="text-3xl font-bold">Beranda</h1>
      <p className="mt-2">Website salon RAG-Salon (placeholder Phase 01).</p>
      <nav className="mt-6 flex flex-col gap-2">
        <a href="/services" className="text-primary underline">
          Layanan
        </a>
        <a href="/reservation" className="text-primary underline">
          Reservasi
        </a>
        <a href="/about" className="text-primary underline">
          Tentang
        </a>
        <a href="/consult" className="text-primary underline">
          Konsultasi Rambut (AI)
        </a>
      </nav>
    </main>
  );
}
