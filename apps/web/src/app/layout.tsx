import { AppShell } from '@/components/layout/app-shell';
import { Analytics } from '@vercel/analytics/next';
import type { Metadata } from 'next';
import { Cormorant_Garamond, DM_Sans } from 'next/font/google';
import './globals.css';

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  variable: '--font-heading',
  weight: ['500', '600', '700'],
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-body',
});

export const metadata: Metadata = {
  metadataBase: new URL('http://localhost:3000'),
  title: {
    default: 'TIEN SALON',
    template: '%s | TIEN SALON',
  },
  description:
    'Website portfolio static TIEN SALON untuk katalog layanan dan simulasi reservasi salon.',
  generator: 'Next.js',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className={`${cormorant.variable} ${dmSans.variable} font-sans antialiased`}>
        <AppShell>{children}</AppShell>
        <Analytics />
      </body>
    </html>
  );
}
