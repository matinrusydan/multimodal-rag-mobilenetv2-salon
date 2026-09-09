export type SplineScene = {
  id: string;
  name: string;
  description: string;
  sceneUrl: string;
};

export const splineScenes: SplineScene[] = [
  {
    id: 'salon-primary',
    name: 'Scene Salon Primary',
    description: 'Scene pertama untuk uji coba visual 3D hero TIEN SALON.',
    sceneUrl: 'https://prod.spline.design/6XP5FPt6hHktxwCk/scene.splinecode',
  },
  {
    id: 'salon-alternate',
    name: 'Scene Salon Alternate',
    description: 'Scene kedua sebagai pembanding visual sebelum dipilih untuk halaman utama.',
    sceneUrl: 'https://prod.spline.design/REcoajNojMA2BF8z/scene.splinecode',
  },
];
