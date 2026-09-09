export interface SalonInfo {
  name: string;
  tagline: string;
  address: string;
  phone: string;
  email: string;
  mapEmbedUrl: string;
  operatingHours: {
    days: string;
    hours: string;
  }[];
  socialLinks: {
    platform: string;
    url: string;
    icon: string;
  }[];
  stats: {
    label: string;
    value: string;
  }[];
}

export const salonInfo: SalonInfo = {
  name: 'TIEN SALON',
  tagline: 'Hair care reservation experience for modern salon rituals.',
  address: 'Jl. Kemang Raya No. 18, Jakarta Selatan, DKI Jakarta',
  phone: '+62 812-3456-7890',
  email: 'hello@tiensalon.com',
  mapEmbedUrl: 'https://www.google.com/maps?q=Kemang%20Jakarta%20Selatan&output=embed',
  operatingHours: [
    { days: 'Senin-Jumat', hours: '08.00-20.00' },
    { days: 'Sabtu-Minggu', hours: '09.00-18.00' },
  ],
  socialLinks: [
    { platform: 'Instagram', url: 'https://instagram.com', icon: 'Instagram' },
    { platform: 'Facebook', url: 'https://facebook.com', icon: 'Facebook' },
    { platform: 'TikTok', url: 'https://tiktok.com', icon: 'TikTok' },
    { platform: 'WhatsApp', url: 'https://wa.me/6281234567890', icon: 'WhatsApp' },
  ],
  stats: [
    { label: 'Pelanggan Puas', value: '500+' },
    { label: 'Tahun Pengalaman', value: '5' },
    { label: 'Layanan', value: '20+' },
  ],
};
