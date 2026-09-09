export interface Testimonial {
  id: string;
  name: string;
  location: string;
  occupation: string;
  content: string;
  rating: number;
  image: string;
}

export const testimonials: Testimonial[] = [
  {
    id: 'tst-001',
    name: 'Nadia Putri',
    location: 'Jakarta Selatan',
    occupation: 'Creative Producer',
    content: 'Hair spa-nya nyaman dan hasil rambut saya jauh lebih lembut setelah treatment.',
    rating: 5,
    image: '/images/testimonials/nadia.svg',
  },
  {
    id: 'tst-002',
    name: 'Aurelia Sari',
    location: 'Tangerang',
    occupation: 'Entrepreneur',
    content: 'Potongan rambutnya presisi dan tetap gampang diatur setelah beberapa hari.',
    rating: 5,
    image: '/images/testimonials/aurelia.svg',
  },
  {
    id: 'tst-003',
    name: 'Mira Lestari',
    location: 'Depok',
    occupation: 'Marketing Lead',
    content: 'Keratin treatment membuat rambut saya lebih halus tanpa terasa terlalu kaku.',
    rating: 5,
    image: '/images/testimonials/mira.svg',
  },
  {
    id: 'tst-004',
    name: 'Citra Amelia',
    location: 'Bekasi',
    occupation: 'Finance Analyst',
    content: 'Scalp detox-nya bikin kulit kepala terasa ringan dan segar.',
    rating: 4,
    image: '/images/testimonials/citra.svg',
  },
  {
    id: 'tst-005',
    name: 'Rachel Tan',
    location: 'Jakarta Barat',
    occupation: 'Content Creator',
    content: 'Color refresh-nya subtle, glossy, dan terlihat bagus di kamera.',
    rating: 5,
    image: '/images/testimonials/rachel.svg',
  },
  {
    id: 'tst-006',
    name: 'Dewi Kartika',
    location: 'Bogor',
    occupation: 'Teacher',
    content: 'Blowout styling-nya awet untuk acara dan tetap natural.',
    rating: 4,
    image: '/images/testimonials/dewi.svg',
  },
];
