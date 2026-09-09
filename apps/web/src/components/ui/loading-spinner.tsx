import { cn } from '@/lib/utils';

type LoadingSpinnerProps = {
  label?: string;
  className?: string;
};

export function LoadingSpinner({ label = 'Memuat...', className }: LoadingSpinnerProps) {
  return (
    <output className={cn('loading-state', className)}>
      <span className="loading-spinner" aria-hidden="true" />
      <span>{label}</span>
    </output>
  );
}
