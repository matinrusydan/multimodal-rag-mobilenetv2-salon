import Image from 'next/image';

import { StarRating } from '@/components/ui/star-rating';
import { testimonials } from '@/data/testimonials';

export function Testimonials() {
  return (
    <section className="site-section testimonials-section">
      <div className="site-container">
        <div className="section-heading section-heading--center">
          <p className="section-heading__eyebrow">Testimoni</p>
          <h2>Apa kata pelanggan</h2>
          <p>Tiga cerita singkat dari mock data untuk memperkuat konteks portfolio.</p>
        </div>
        <div className="testimonial-grid">
          {testimonials.slice(0, 3).map((testimonial) => (
            <article key={testimonial.id} className="testimonial-card">
              <StarRating rating={testimonial.rating} />
              <p>&quot;{testimonial.content}&quot;</p>
              <div className="testimonial-card__person">
                <Image
                  src={testimonial.image}
                  alt={`Avatar ${testimonial.name}`}
                  width={56}
                  height={56}
                />
                <div>
                  <strong>{testimonial.name}</strong>
                  <span>{testimonial.location}</span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
