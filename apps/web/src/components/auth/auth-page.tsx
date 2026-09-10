'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect } from 'react';

import { AuthForm, type AuthMode } from '@/components/auth/auth-form';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { useAuth } from '@/lib/use-auth';

const IMAGE_SRC =
  'https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Image%20Register%20%26%20Login.png-39LkbTrMTCBx60lPiN4zkPodueYnEw.jpeg';

const MORPH_TRANSITION = { type: 'spring' as const, stiffness: 200, damping: 26, mass: 0.7 };

export function AuthPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoggedIn, isReady } = useAuth();

  const mode: AuthMode = searchParams.get('mode') === 'register' ? 'register' : 'login';
  const redirect = searchParams.get('redirect') ?? undefined;

  useEffect(() => {
    if (isReady && isLoggedIn) {
      router.replace(redirect || '/home');
    }
  }, [isLoggedIn, isReady, redirect, router]);

  if (!isReady || isLoggedIn) {
    return <LoadingSpinner label="Memeriksa status login..." />;
  }

  return (
    <div className="auth-figma-page">
      <div className="auth-figma-flow">
        <div className="auth-figma-back-wrap">
          <Link href="/home" className="auth-figma-back-link">
            <ArrowLeft size={16} />
            Kembali ke Beranda
          </Link>
        </div>

        <AnimatePresence initial={false} mode="popLayout">
          <motion.div
            key={mode}
            className="auth-figma-grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            {mode === 'register' ? (
              <>
                <motion.div
                  className="auth-figma-visual"
                  layoutId="auth-visual-panel"
                  transition={MORPH_TRANSITION}
                >
                  <img
                    src={IMAGE_SRC}
                    alt="Beauty workspace illustration"
                    className="auth-figma-visual-image"
                  />
                </motion.div>
                <motion.div
                  className="auth-figma-panel"
                  layoutId="auth-form-panel"
                  transition={MORPH_TRANSITION}
                >
                  <AuthForm mode={mode} redirect={redirect} />
                </motion.div>
              </>
            ) : (
              <>
                <motion.div
                  className="auth-figma-panel"
                  layoutId="auth-form-panel"
                  transition={MORPH_TRANSITION}
                >
                  <AuthForm mode={mode} redirect={redirect} />
                </motion.div>
                <motion.div
                  className="auth-figma-visual"
                  layoutId="auth-visual-panel"
                  transition={MORPH_TRANSITION}
                >
                  <img
                    src={IMAGE_SRC}
                    alt="Beauty workspace illustration"
                    className="auth-figma-visual-image"
                  />
                </motion.div>
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
