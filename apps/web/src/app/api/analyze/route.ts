import { problem, routeError } from '@/lib/backend';

export async function POST() {
  return routeError(
    problem(
      503,
      'Fitur belum tersedia',
      'Analisis foto belum tersedia. Silakan gunakan konsultasi teks.',
    ),
  );
}
