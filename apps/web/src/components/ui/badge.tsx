import type React from 'react';

import { cn } from '@/lib/utils';

type BadgeProps = {
  children: React.ReactNode;
  tone?: 'rose' | 'amber' | 'success' | 'neutral';
  className?: string;
};

export function Badge({ children, tone = 'rose', className }: BadgeProps) {
  return <span className={cn('badge', `badge--${tone}`, className)}>{children}</span>;
}
