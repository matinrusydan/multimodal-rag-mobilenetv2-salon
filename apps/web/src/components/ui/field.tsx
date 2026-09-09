import type React from 'react';

import { cn } from '@/lib/utils';

type FieldProps = {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
  className?: string;
};

export function Field({ label, htmlFor, error, hint, children, className }: FieldProps) {
  return (
    <div className={cn('form-field', className)}>
      <label htmlFor={htmlFor}>{label}</label>
      {children}
      {hint ? <p className="form-field__hint">{hint}</p> : null}
      {error ? <p className="form-field__error">{error}</p> : null}
    </div>
  );
}
