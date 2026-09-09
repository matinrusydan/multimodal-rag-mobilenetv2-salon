import { Star } from 'lucide-react';

const STARS = [0, 1, 2, 3, 4];

type StarRatingProps = {
  rating: number;
};

export function StarRating({ rating }: StarRatingProps) {
  return (
    <div className="star-rating" aria-label={`Rating ${rating} dari 5`}>
      {STARS.map((position) => (
        <Star
          key={position}
          size={16}
          fill={position < rating ? 'currentColor' : 'none'}
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
