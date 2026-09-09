import type { Config } from 'tailwindcss';
import animate from 'tailwindcss-animate';

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#6d28d9',
          foreground: '#ffffff',
        },
        accent: {
          DEFAULT: '#f5f3ff',
          foreground: '#4c1d95',
        },
      },
    },
  },
  plugins: [animate],
};

export default config;
