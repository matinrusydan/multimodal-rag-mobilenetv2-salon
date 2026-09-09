export function formatRupiah(value: number): string {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('id-ID', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
}

export function getTomorrowInputValue(): string {
  const date = new Date();
  date.setDate(date.getDate() + 1);

  return date.toISOString().slice(0, 10);
}

export function isPastTimeForDate(dateValue: string, timeValue: string): boolean {
  if (!dateValue) {
    return false;
  }

  const now = new Date();
  const today = now.toISOString().slice(0, 10);

  if (dateValue !== today) {
    return false;
  }

  const [hour, minute] = timeValue.split(':').map(Number);
  const selected = new Date();
  selected.setHours(hour, minute, 0, 0);

  return selected <= now;
}
