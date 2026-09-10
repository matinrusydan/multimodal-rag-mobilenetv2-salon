'use client';

import { type Service, getFeaturedServices } from '@/data/services';
import { type MotionValue, motion, useScroll, useTransform } from 'framer-motion';
import { ArrowDown, Clock } from 'lucide-react';
import Image from 'next/image';
import { useEffect, useRef, useState } from 'react';

interface StackedCardProps {
  service: Service;
  index: number;
  totalCards: number;
  scrollYProgress: MotionValue<number>;
  multiplier: number;
  handleReservasi: (service: Service) => void;
}

function StackedCard({
  service,
  index,
  totalCards,
  scrollYProgress,
  multiplier,
  handleReservasi,
}: StackedCardProps) {
  // 1. Initial Fan-out parameters (at scroll = 0)
  const xInit = [-180, -60, 60, 180][index] * multiplier;
  const yInit = [16, 4, 4, 16][index];
  const rotateInit = [-8, -2.5, 2.5, 8][index];

  // 2. Morph fanned-out bottom-right parameters (at scroll = 1)
  const xMorph = [30, 140, 250, 360][index] * multiplier;
  const yMorph = [50, 80, 105, 125][index] * multiplier;
  const rotateMorph = [-10, -4, 2, 8][index];

  const zIndex = (totalCards - index) * 10;

  // Continuous animation ranges mapping scroll progress to coordinates
  const progressPoints = [0, 0.28, 0.45, 1.0];
  const x = useTransform(scrollYProgress, progressPoints, [xInit, 0, 0, xMorph]);
  const y = useTransform(scrollYProgress, progressPoints, [yInit, 0, 0, yMorph]);
  const rotate = useTransform(scrollYProgress, progressPoints, [rotateInit, 0, 0, rotateMorph]);

  // Format currency
  const formatRupiah = (val: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  return (
    <motion.div
      onClick={() => handleReservasi(service)}
      style={{
        x,
        y,
        rotate,
        zIndex,
        backgroundColor: service.color,
        transformOrigin: 'center bottom',
      }}
      className="absolute w-[230px] h-[230px] sm:w-[275px] sm:h-[275px] rounded-[1.75rem] p-5 shadow-[0_12px_36px_rgba(136,14,79,0.08)] border border-white/25 flex flex-col justify-between select-none overflow-hidden cursor-pointer hover:scale-[1.03] transition-all duration-300 active:scale-[0.98] group"
    >
      {/* Decorative inner gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-br from-white/15 to-black/5 pointer-events-none" />

      {/* Top Header Row */}
      <div className="z-10 flex justify-between items-start">
        <span className="text-[9px] uppercase tracking-widest text-[#4A1525]/60 font-extrabold">
          {service.category}
        </span>
        <span className="text-[9px] text-[#4A1525]/75 bg-white/20 px-2 py-0.5 rounded-full font-bold">
          {service.durationMinutes} Min
        </span>
      </div>

      {/* Center Image Container */}
      <div className="z-10 flex-1 flex justify-center items-center my-1">
        <div className="relative w-16 h-16 sm:w-20 sm:h-20 bg-white/15 backdrop-blur-sm rounded-[1.25rem] p-2 flex justify-center items-center shadow-inner">
          <Image
            src={service.image}
            alt={service.name}
            width={64}
            height={64}
            className="object-contain max-w-[85%] max-h-[85%] drop-shadow-[0_4px_8px_rgba(0,0,0,0.06)]"
            priority
          />
        </div>
      </div>

      {/* Bottom Service Info & Pricing */}
      <div className="z-10 text-[#3B111A] pt-2 border-t border-[#4A1525]/10">
        <h3 className="text-xs sm:text-sm font-bold font-playfair tracking-tight leading-snug mb-0.5 line-clamp-1">
          {service.name}
        </h3>
        <div className="flex items-center justify-between">
          <span className="text-xs font-extrabold text-[#880E4F]">
            {formatRupiah(service.discountPrice || service.price)}
          </span>
          <span className="text-[9px] text-[#880E4F] font-bold group-hover:translate-x-0.5 transition-transform duration-200">
            Reservasi →
          </span>
        </div>
      </div>
    </motion.div>
  );
}

export function StackedServicesScroll() {
  const containerRef = useRef<HTMLDivElement>(null);
  const featuredServices = getFeaturedServices();

  // Track scroll position of the tall container
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end'],
  });

  // Responsive multiplier state for horizontal fanned spread
  const [multiplier, setMultiplier] = useState(1);

  useEffect(() => {
    const handleResize = () => {
      if (typeof window === 'undefined') return;
      if (window.innerWidth < 640) {
        setMultiplier(0.12); // Highly compact for small screens
      } else if (window.innerWidth < 1024) {
        setMultiplier(0.65); // Tablet
      } else {
        setMultiplier(1.0); // Desktop
      }
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleReservasi = (service: Service) => {
    if (typeof window === 'undefined') return;

    const reservationData = {
      customerName: '',
      email: '',
      phone: '',
      serviceId: service.id,
      serviceName: service.name,
      servicePrice: service.discountPrice || service.price,
      date: '',
      time: '',
      notes: '',
      invoiceNumber: `INV-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.floor(1000 + Math.random() * 9000)}`,
    };

    sessionStorage.setItem('tien_reservation', JSON.stringify(reservationData));

    const authDataStr = sessionStorage.getItem('tien_auth');
    if (authDataStr) {
      try {
        const auth = JSON.parse(authDataStr);
        if (auth.isLoggedIn) {
          window.location.href = '/reservation';
          return;
        }
      } catch (e) {
        console.error(e);
      }
    }

    window.location.href = '/auth';
  };

  // Fade out indicators when scrolling begins
  const indicatorsOpacity = useTransform(scrollYProgress, [0, 0.12], [1, 0]);

  // Fade out Heading 1 (Center) as we scroll down to stack
  const heading1Opacity = useTransform(scrollYProgress, [0.28, 0.45], [1, 0]);
  const heading1Y = useTransform(scrollYProgress, [0.28, 0.45], [0, -35]);

  // Fade in Heading 2 (Left Experience Morph block) during the transition to bottom-right fan
  const heading2Opacity = useTransform(scrollYProgress, [0.45, 0.72], [0, 1]);
  const heading2Y = useTransform(scrollYProgress, [0.45, 0.72], [30, 0]);

  // Apply conditional class pointer-events depending on visibility
  const [isMorphActive, setIsMorphActive] = useState(false);
  useEffect(() => {
    return scrollYProgress.on('change', (latest) => {
      setIsMorphActive(latest > 0.45);
    });
  }, [scrollYProgress]);

  return (
    <div
      ref={containerRef}
      className="relative w-full min-h-[220vh] sm:min-h-[240vh] md:min-h-[260vh] bg-gradient-to-b from-[#faf6f0] to-white"
    >
      {/* Sticky Frame: Locks everything in the viewport */}
      <div className="sticky top-0 w-full h-screen overflow-hidden flex flex-col justify-between py-12 md:py-16">
        {/* Section Heading 1 (Initial State - Centered) */}
        <motion.div
          style={{ opacity: heading1Opacity, y: heading1Y }}
          className="absolute top-12 md:top-20 left-0 right-0 text-center px-4 max-w-2xl mx-auto z-20 pointer-events-none"
        >
          <p className="text-xs uppercase tracking-[0.3em] text-[#880E4F] font-semibold mb-2">
            Layanan Unggulan
          </p>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-playfair font-extrabold text-[#3B111A]">
            Ritual Rambut Favorit
          </h2>
          <p className="text-xs sm:text-sm text-gray-500 mt-2 max-w-md mx-auto">
            Scroll ke bawah untuk merapatkan kartu layanan.
          </p>
        </motion.div>

        {/* Floating Stacked Cards Deck Area & Morph Section Content Container */}
        <div className="relative flex-1 w-full max-w-7xl mx-auto px-6 sm:px-12 md:px-16 flex items-center h-full">
          {/* Left Column: Heading 2 experience morph block */}
          <motion.div
            style={{ opacity: heading2Opacity, y: heading2Y }}
            className={`absolute top-16 left-6 right-6 md:top-1/2 md:-translate-y-1/2 md:left-12 lg:left-20 w-auto md:max-w-[400px] text-center md:text-left flex flex-col items-center md:items-start z-20 ${
              isMorphActive ? 'pointer-events-auto' : 'pointer-events-none'
            }`}
          >
            <span className="text-xs uppercase tracking-[0.3em] text-[#880E4F] font-semibold mb-2 block">
              TIEN SALON EXPERIENCE
            </span>
            <h2 className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-playfair font-extrabold text-[#3B111A] leading-tight mb-4">
              Detail Kecil yang Istimewa
            </h2>
            <p className="text-xs sm:text-sm text-gray-600 leading-relaxed mb-6">
              Nuansa salon dirancang clean, feminin, dan menenangkan untuk perawatan rambut Anda.
              Kami mengutamakan produk berkualitas tinggi serta pelayanan dari terapis profesional
              untuk memberikan hasil terbaik.
            </p>
            <a
              href="/about"
              className="px-6 py-3 bg-[#880E4F] hover:bg-[#6F123F] text-white text-xs sm:text-sm font-bold rounded-full transition-all duration-300 shadow-md hover:shadow-lg focus:outline-none hover:-translate-y-0.5 active:translate-y-0"
            >
              Tentang Kami
            </a>
          </motion.div>

          {/* Right/Centered Card Deck */}
          <div className="relative w-full flex items-center justify-center min-h-[300px] md:h-[450px]">
            <div className="relative w-full max-w-[280px] sm:max-w-[325px] h-[280px] sm:h-[325px] flex items-center justify-center">
              {featuredServices.map((service, index) => (
                <StackedCard
                  key={service.id}
                  service={service}
                  index={index}
                  totalCards={featuredServices.length}
                  scrollYProgress={scrollYProgress}
                  multiplier={multiplier}
                  handleReservasi={handleReservasi}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Scroll Helper Prompt Indicator */}
        <motion.div
          style={{ opacity: indicatorsOpacity }}
          className="text-center flex flex-col items-center justify-center gap-1.5 text-gray-400 select-none z-20 pb-4"
        >
          <span className="text-[10px] font-semibold uppercase tracking-[0.25em] animate-pulse">
            Scroll ke bawah
          </span>
          <motion.div
            animate={{ y: [0, 5, 0] }}
            transition={{ repeat: Number.POSITIVE_INFINITY, duration: 1.5, ease: 'easeInOut' }}
          >
            <ArrowDown size={14} className="text-[#880E4F]" />
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
