export const JAM_OPTIONS = [
  '08:00',
  '09:00',
  '10:00',
  '11:00',
  '12:00',
  '13:00',
  '14:00',
  '15:00',
  '16:00',
  '17:00',
  '18:00',
  '19:00',
];

export const SESSION_KEYS = {
  auth: 'tien_auth',
  reservation: 'tien_reservation',
  payment: 'tien_payment',
} as const;

export const NAV_ITEMS = [
  { label: 'Beranda', href: '/home' },
  { label: 'Layanan', href: '/services' },
  { label: 'Konsultasi', href: '/consult' },
  { label: 'Tentang', href: '/about' },
  { label: 'Kontak', href: '/contact' },
];
