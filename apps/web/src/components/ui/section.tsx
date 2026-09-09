import type React from 'react';

import { cn } from '@/lib/utils';

type SectionProps = {
  eyebrow?: string;
  title?: string;
  description?: string;
  children?: React.ReactNode;
  className?: string;
  contentClassName?: string;
};

export function Section({
  eyebrow,
  title,
  description,
  children,
  className,
  contentClassName,
}: SectionProps) {
  return (
    <section className={cn('site-section', className)}>
      <div className={cn('site-container', contentClassName)}>
        {title || description || eyebrow ? (
          <div className="section-heading">
            {eyebrow ? <p className="section-heading__eyebrow">{eyebrow}</p> : null}
            {title ? <h2>{title}</h2> : null}
            {description ? <p>{description}</p> : null}
          </div>
        ) : null}
        {children}
      </div>
    </section>
  );
}
