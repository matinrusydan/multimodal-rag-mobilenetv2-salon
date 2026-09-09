import type React from 'react';

import { SiteFooter } from '@/components/layout/site-footer';
import { SiteHeader } from '@/components/layout/site-header';
import { cn } from '@/lib/utils';

type MarketingShellProps = {
  children: React.ReactNode;
  className?: string;
};

export function MarketingShell({ children, className }: MarketingShellProps) {
  return (
    <div className={cn('site-shell', className)}>
      <SiteHeader />
      <main>{children}</main>
      <SiteFooter />
    </div>
  );
}
