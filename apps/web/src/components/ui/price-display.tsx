import { formatRupiah } from '@/lib/format';
import { cn } from '@/lib/utils';

type PriceDisplayProps = {
  price: number;
  discountPrice?: number;
  className?: string;
};

export function PriceDisplay({ price, discountPrice, className }: PriceDisplayProps) {
  return (
    <div className={cn('price-display', className)}>
      {discountPrice ? <span>{formatRupiah(price)}</span> : null}
      <strong>{formatRupiah(discountPrice ?? price)}</strong>
    </div>
  );
}
