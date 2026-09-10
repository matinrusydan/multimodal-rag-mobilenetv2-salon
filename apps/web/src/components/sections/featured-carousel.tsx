'use client';

import { getFeaturedServices } from '@/data/services';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, ArrowRight, CheckCircle, Clock } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';

export function FeaturedServicesCarousel() {
  const featuredServices = getFeaturedServices();
  const [[page, direction], setPage] = useState([0, 0]);

  const activeIndex =
    ((page % featuredServices.length) + featuredServices.length) % featuredServices.length;
  const activeService = featuredServices[activeIndex];

  const paginate = (newDirection: number) => {
    setPage([page + newDirection, newDirection]);
  };

  const setSlide = (index: number) => {
    const dir = index > activeIndex ? 1 : -1;
    const diff = index - activeIndex;
    setPage([page + diff, dir]);
  };

  const handleReservasi = () => {
    if (typeof window === 'undefined') return;

    // Pre-populate reservation state in sessionStorage for redirection
    const reservationData = {
      customerName: '',
      email: '',
      phone: '',
      serviceId: activeService.id,
      serviceName: activeService.name,
      servicePrice: activeService.discountPrice || activeService.price,
      date: '',
      time: '',
      notes: '',
      invoiceNumber: `INV-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}-${Math.floor(1000 + Math.random() * 9000)}`,
    };

    sessionStorage.setItem('tien_reservation', JSON.stringify(reservationData));

    // Check if logged in, if not redirect to login, else go directly to reservation
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

  // Format currency
  const formatRupiah = (val: number) => {
    return new Intl.NumberFormat('id-ID', {
      style: 'currency',
      currency: 'IDR',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const imageVariants = {
    enter: (dir: number) => ({
      x: dir > 0 ? 160 : -160,
      opacity: 0,
      scale: 0.85,
    }),
    center: {
      x: 0,
      opacity: 1,
      scale: 1,
      transition: {
        x: { type: 'spring' as const, stiffness: 300, damping: 30 },
        opacity: { duration: 0.4 },
        scale: { duration: 0.4 },
      },
    },
    exit: (dir: number) => ({
      x: dir < 0 ? 160 : -160,
      opacity: 0,
      scale: 0.85,
      transition: {
        x: { type: 'spring' as const, stiffness: 300, damping: 30 },
        opacity: { duration: 0.3 },
        scale: { duration: 0.3 },
      },
    }),
  };

  const textVariants = {
    initial: { opacity: 0, y: 15 },
    animate: { opacity: 1, y: 0, transition: { duration: 0.4 } },
    exit: { opacity: 0, y: -15, transition: { duration: 0.3 } },
  };

  return (
    <div className="pallet-ross-carousel w-full py-12">
      {/* Editorial Header Section */}
      <div className="mb-10 text-center md:text-left">
        <p className="text-xs uppercase tracking-[0.3em] text-gray-500 font-semibold mb-2">
          Discover the Art of
        </p>
        <div className="h-[90px] overflow-hidden relative flex flex-col justify-center items-center md:items-start">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeService.category}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -30 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
              className="flex flex-col md:flex-row items-center gap-x-4 select-none"
            >
              <h2 className="font-playfair text-4xl sm:text-5xl md:text-6xl font-bold text-[var(--color-dark)] tracking-tight">
                {activeService.category.split(' ')[0]}
              </h2>
              <span className="font-playfair text-4xl sm:text-5xl md:text-6xl font-light text-stroke tracking-normal opacity-50">
                {activeService.category.split(' ').slice(1).join(' ') || 'treatment.'}
              </span>
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Main Interactive Card Container */}
      <motion.div
        animate={{ backgroundColor: activeService.color }}
        transition={{ duration: 0.8, ease: 'easeInOut' }}
        className="relative rounded-[2.5rem] p-6 sm:p-10 md:p-14 shadow-2xl overflow-hidden min-h-[480px] sm:min-h-[520px] md:min-h-[580px] flex flex-col justify-between"
      >
        {/* Glow/Overlay effects inside card */}
        <div className="absolute inset-0 bg-gradient-to-tr from-black/10 via-transparent to-white/10 pointer-events-none" />
        <div className="absolute top-[-30%] left-[-20%] w-[70%] h-[70%] bg-white/20 rounded-full blur-[100px] pointer-events-none" />

        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-center h-full my-auto z-10">
          {/* Swatches (Vertical Pill) - Grid col 1 */}
          <div className="col-span-1 md:col-span-1 flex md:flex-col justify-center items-center gap-4">
            <div className="flex md:flex-col items-center gap-3 bg-black/15 backdrop-blur-md p-2 rounded-full border border-white/20 shadow-lg">
              {featuredServices.map((service, idx) => {
                const isActive = activeIndex === idx;
                return (
                  <button
                    key={service.id}
                    type="button"
                    onClick={() => setSlide(idx)}
                    className="relative w-8 h-8 rounded-full focus:outline-none transition-all duration-300 hover:scale-110 flex items-center justify-center cursor-pointer"
                    aria-label={`Lihat layanan ${service.name}`}
                  >
                    {isActive && (
                      <motion.div
                        layoutId="activeSwatchIndicator"
                        className="absolute inset-0 bg-white rounded-full shadow-md"
                        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                      />
                    )}
                    <span
                      className="absolute w-3 h-3 rounded-full z-10 transition-colors"
                      style={{
                        backgroundColor: isActive ? '#333333' : service.color,
                        boxShadow: isActive ? 'none' : '0 0 4px rgba(0,0,0,0.2)',
                      }}
                    />
                  </button>
                );
              })}
            </div>
          </div>

          {/* Model/Illustration Container - Grid col 6 on Desktop */}
          <div className="col-span-1 md:col-span-6 flex justify-center items-center min-h-[220px] sm:min-h-[260px] md:min-h-[340px] relative order-first md:order-none">
            <div className="relative w-[200px] h-[200px] sm:w-[240px] sm:h-[240px] md:w-[320px] md:h-[320px] flex justify-center items-center">
              <AnimatePresence initial={false} custom={direction} mode="wait">
                <motion.div
                  key={page}
                  custom={direction}
                  variants={imageVariants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  className="absolute inset-0 flex justify-center items-center"
                >
                  <div className="relative w-full h-full bg-white/20 backdrop-blur-sm rounded-[2rem] p-4 flex justify-center items-center shadow-inner">
                    <Image
                      src={activeService.image}
                      alt={activeService.name}
                      width={280}
                      height={280}
                      className="object-contain max-w-[85%] max-h-[85%] drop-shadow-[0_10px_15px_rgba(0,0,0,0.15)] filter brightness-105"
                      priority
                    />
                  </div>
                </motion.div>
              </AnimatePresence>
            </div>
          </div>

          {/* Text Details & Action Button - Grid col 5 */}
          <div className="col-span-1 md:col-span-5 flex flex-col justify-center text-white text-center md:text-left select-none">
            <AnimatePresence mode="wait">
              <motion.div
                key={page}
                variants={textVariants}
                initial="initial"
                animate="animate"
                exit="exit"
                className="flex flex-col gap-4"
              >
                <div className="flex flex-wrap gap-2 items-center justify-center md:justify-start">
                  <span className="bg-white/20 backdrop-blur-md px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider flex items-center gap-1 border border-white/10">
                    <Clock size={12} /> {activeService.durationMinutes} Menit
                  </span>
                  {activeService.discountPrice && (
                    <span className="bg-[#C2185B] text-white px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider">
                      Promo Hemat
                    </span>
                  )}
                </div>

                <h3 className="text-2xl sm:text-3xl md:text-4xl font-bold font-playfair tracking-tight leading-tight">
                  {activeService.name}
                </h3>

                <p className="text-white/90 text-sm leading-relaxed max-w-md mx-auto md:mx-0">
                  {activeService.shortDescription}
                </p>

                {/* Benefits checklist */}
                <ul className="flex flex-col gap-1.5 text-xs text-white/85 text-left max-w-sm mx-auto md:mx-0">
                  {activeService.benefits.slice(0, 3).map((benefit) => (
                    <li key={benefit} className="flex items-center gap-2">
                      <CheckCircle size={14} className="text-white shrink-0" />
                      <span>{benefit}</span>
                    </li>
                  ))}
                </ul>

                {/* Prices */}
                <div className="mt-2 flex items-baseline justify-center md:justify-start gap-3">
                  {activeService.discountPrice ? (
                    <>
                      <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                        {formatRupiah(activeService.discountPrice)}
                      </span>
                      <span className="text-sm line-through text-white/60">
                        {formatRupiah(activeService.price)}
                      </span>
                    </>
                  ) : (
                    <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {formatRupiah(activeService.price)}
                    </span>
                  )}
                </div>

                {/* Action CTA */}
                <div className="mt-4">
                  <button
                    type="button"
                    onClick={handleReservasi}
                    className="w-full sm:w-auto px-8 py-3 bg-white text-[var(--color-dark)] font-bold rounded-full hover:bg-neutral-100 transition-all duration-300 hover:shadow-lg focus:outline-none hover:-translate-y-0.5 active:translate-y-0 active:shadow-md cursor-pointer"
                  >
                    Reservasi Sekarang
                  </button>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Bottom Pagination & Navigation - Arrows */}
        <div className="flex justify-between items-center mt-8 pt-6 border-t border-white/10 z-10">
          <div className="text-xs text-white/70 uppercase tracking-widest font-semibold">
            {activeIndex + 1} / {featuredServices.length}
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => paginate(-1)}
              className="w-10 h-10 rounded-full border border-white/20 bg-white/10 hover:bg-white/20 text-white flex items-center justify-center backdrop-blur-sm transition-all duration-300 active:scale-95 focus:outline-none cursor-pointer"
              aria-label="Layanan sebelumnya"
            >
              <ArrowLeft size={18} />
            </button>
            <button
              type="button"
              onClick={() => paginate(1)}
              className="w-10 h-10 rounded-full border border-white/20 bg-white/10 hover:bg-white/20 text-white flex items-center justify-center backdrop-blur-sm transition-all duration-300 active:scale-95 focus:outline-none cursor-pointer"
              aria-label="Layanan berikutnya"
            >
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
