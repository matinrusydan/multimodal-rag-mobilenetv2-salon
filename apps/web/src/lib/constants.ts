export const NAV_ITEMS = [
  { label: 'Beranda', href: '/home' },
  { label: 'Layanan', href: '/services' },
  { label: 'Reservasi', href: '/reservation' },
  { label: 'Konsultasi', href: '/consult' },
  { label: 'Tentang', href: '/about' },
  { label: 'Kontak', href: '/contact' },
] as const;

export const SESSION_KEYS = {
  auth: 'tien-auth',
  reservation: 'tien-reservation',
  payment: 'tien-payment',
} as const;

export const SESSION_NAME = 'rag-salon-session';
