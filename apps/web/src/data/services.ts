export interface Service {
  id: string;
  name: string;
  slug: string;
  shortDescription: string;
  description: string;
  image: string;
  price: number;
  discountPrice?: number;
  durationMinutes: number;
  isFeatured: boolean;
  benefits: string[];
  category: string;
  color: string;
}

export const services: Service[] = [
  {
    id: 'svc-001',
    name: 'Signature Hair Spa',
    slug: 'signature-hair-spa',
    shortDescription: 'Perawatan rambut premium untuk rambut lebih lembut, sehat, dan berkilau.',
    description:
      'Ritual hair spa khas TIEN SALON dengan pijatan relaksasi kulit kepala, masker rambut bernutrisi, dan finishing lembut untuk mengembalikan kelembapan rambut.',
    image: '/images/services/creambath.png',
    price: 325000,
    discountPrice: 285000,
    durationMinutes: 90,
    isFeatured: true,
    benefits: [
      'Melembapkan rambut kering',
      'Mengurangi rambut kusut',
      'Relaksasi kulit kepala',
      'Finishing blow natural',
    ],
    category: 'Hair Treatment',
    color: '#E8B4B8',
  },
  {
    id: 'svc-002',
    name: 'Precision Haircut',
    slug: 'precision-haircut',
    shortDescription:
      'Potongan rambut presisi yang disesuaikan dengan karakter rambut dan gaya personal.',
    description:
      'Layanan haircut dengan konsultasi singkat, shaping presisi, dan styling akhir agar potongan rambut terasa rapi, ringan, dan mudah diatur.',
    image: '/images/services/haircut.png',
    price: 220000,
    durationMinutes: 60,
    isFeatured: true,
    benefits: [
      'Konsultasi bentuk potongan',
      'Layer dan framing presisi',
      'Cocok untuk refresh style',
      'Finishing styling ringan',
    ],
    category: 'Haircut',
    color: '#A3B899',
  },
  {
    id: 'svc-003',
    name: 'Keratin Smooth Treatment',
    slug: 'keratin-smooth-treatment',
    shortDescription: 'Treatment keratin untuk rambut tampak lebih halus, jatuh, dan mudah ditata.',
    description:
      'Perawatan keratin untuk membantu mengurangi tampilan frizz dan membuat rambut terasa lebih halus tanpa menghilangkan karakter natural rambut.',
    image: '/images/services/smoothing.png',
    price: 780000,
    discountPrice: 690000,
    durationMinutes: 150,
    isFeatured: true,
    benefits: [
      'Mengurangi frizz',
      'Rambut terasa lebih halus',
      'Membantu rambut mudah diatur',
      'Hasil tampak sleek natural',
    ],
    category: 'Smoothing',
    color: '#C9B3A8',
  },
  {
    id: 'svc-004',
    name: 'Color Gloss Refresh',
    slug: 'color-gloss-refresh',
    shortDescription: 'Refresh warna rambut dengan hasil glossy dan dimensi warna yang lembut.',
    description:
      'Layanan pewarnaan rambut untuk menyegarkan tone, menambah kilau, dan membuat warna rambut terlihat lebih hidup dengan hasil tetap elegan.',
    image: '/images/services/coloring.png',
    price: 620000,
    durationMinutes: 130,
    isFeatured: true,
    benefits: [
      'Refresh tone rambut',
      'Hasil glossy',
      'Dimensi warna lembut',
      'Konsultasi shade sebelum treatment',
    ],
    category: 'Hair Coloring',
    color: '#B3A8C9',
  },
  {
    id: 'svc-005',
    name: 'Scalp Detox Therapy',
    slug: 'scalp-detox-therapy',
    shortDescription: 'Terapi kulit kepala untuk rasa lebih ringan, segar, dan bersih.',
    description:
      'Ritual detox kulit kepala dengan cleansing, massage, dan tonic care untuk membantu rambut terasa lebih ringan dari akar.',
    image: '/images/services/treatment.png',
    price: 360000,
    durationMinutes: 75,
    isFeatured: false,
    benefits: [
      'Membersihkan buildup',
      'Kulit kepala terasa segar',
      'Massage relaksasi',
      'Cocok sebelum hair treatment',
    ],
    category: 'Scalp Care',
    color: '#A2B9BC',
  },
  {
    id: 'svc-006',
    name: 'Volume Blowout Styling',
    slug: 'volume-blowout-styling',
    shortDescription: 'Blow styling bervolume untuk tampilan rambut rapi dan siap acara.',
    description:
      'Styling rambut dengan blowout natural untuk memberi volume, movement, dan hasil akhir yang rapi tanpa terlihat berlebihan.',
    image: '/images/services/hairstyle.png',
    price: 280000,
    durationMinutes: 55,
    isFeatured: false,
    benefits: [
      'Volume natural',
      'Rambut terlihat rapi',
      'Cocok untuk acara',
      'Finishing lembut dan ringan',
    ],
    category: 'Hair Styling',
    color: '#B5838D',
  },
];

export function getFeaturedServices() {
  return services.filter((service) => service.isFeatured).slice(0, 4);
}

export function getServiceBySlug(slug: string) {
  return services.find((service) => service.slug === slug);
}

export function getServiceById(id: string) {
  return services.find((service) => service.id === id);
}
