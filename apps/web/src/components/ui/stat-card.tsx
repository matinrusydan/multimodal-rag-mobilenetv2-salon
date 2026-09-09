import { cn } from '@/lib/utils';

type StatCardProps = {
  value: string;
  label: string;
  description?: string;
  className?: string;
};

export function StatCard({ value, label, description, className }: StatCardProps) {
  return (
    <article className={cn('stat-card', className)}>
      <strong>{value}</strong>
      <span>{label}</span>
      {description ? <p>{description}</p> : null}
    </article>
  );
}
