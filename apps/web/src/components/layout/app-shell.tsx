'use client';

import { AnimatePresence, LayoutGroup, motion } from 'framer-motion';
import { usePathname } from 'next/navigation';
import type React from 'react';

import PageTransitionWrapper from '@/components/layout/page-transition-wrapper';
import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const pathname = usePathname();
  const isSplash = pathname === '/';
  const isAuth = pathname === '/login' || pathname === '/register';

  if (isSplash || isAuth) {
    return (
      <LayoutGroup id="auth-flow">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div key={pathname} className="w-full min-h-screen">
            <main>{children}</main>
          </motion.div>
        </AnimatePresence>
      </LayoutGroup>
    );
  }

  return (
    <div className="site-shell">
      <SiteHeader />
      <PageTransitionWrapper>
        <main>{children}</main>
      </PageTransitionWrapper>
      <SiteFooter />
    </div>
  );
}
