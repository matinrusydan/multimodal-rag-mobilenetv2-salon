/** Format angka ke format Rupiah: Rp 75.000 */
export function formatRupiah(value: number): string {
  const formatted = new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0,
  }).format(value);
  return formatted;
}

/** Format tanggal ISO `YYYY-MM-DD` ke tampilan Indonesia. */
export function formatDate(isoDate: string): string {
  const date = new Date(isoDate);
  return new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date);
}

/** Format waktu `HH:mm` aman. */
export function formatTime(time: string): string {
  return time;
}
