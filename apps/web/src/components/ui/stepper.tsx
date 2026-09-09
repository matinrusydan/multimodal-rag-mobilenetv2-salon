import { cn } from '@/lib/utils';

export type StepperItem = {
  label: string;
  description?: string;
};

type StepperProps = {
  items: StepperItem[];
  activeIndex?: number;
  className?: string;
};

export function Stepper({ items, activeIndex = 0, className }: StepperProps) {
  return (
    <ol className={cn('stepper', className)}>
      {items.map((item, index) => (
        <li
          key={item.label}
          className={cn(
            'stepper__item',
            index < activeIndex && 'stepper__item--done',
            index === activeIndex && 'stepper__item--active',
          )}
        >
          <span className="stepper__number">{index + 1}</span>
          <div>
            <strong>{item.label}</strong>
            {item.description ? <p>{item.description}</p> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
