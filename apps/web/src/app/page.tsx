import Link from 'next/link';

export default function SplashPage() {
  return (
    <main className="flex min-h-svh flex-col items-center justify-center gap-4 p-6 text-center">
      <h1 className="text-4xl font-bold">RAG-Salon</h1>
      <p className="text-muted-foreground">
        Salon kecantikan & konsultasi rambut cerdas berbasis AI
      </p>
      <Link
        href="/home"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
      >
        Masuk ke website
      </Link>
    </main>
  );
}
