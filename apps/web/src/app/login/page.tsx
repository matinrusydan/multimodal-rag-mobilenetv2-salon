'use client';

import { motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, Lock, User } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect, useState } from 'react';

import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { writeSession } from '@/lib/session';
import { notifyAuthChange, useAuth } from '@/lib/use-auth';

export default function LoginPage() {
  const router = useRouter();
  const { isLoggedIn, isReady } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    emailOrUsername: '',
    password: '',
  });

  useEffect(() => {
    if (isReady && isLoggedIn) {
      router.replace('/home');
    }
  }, [isLoggedIn, isReady, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Save auth session data
    writeSession(SESSION_KEYS.auth, {
      isLoggedIn: true,
      user: {
        name: 'Pelanggan Demo',
        email: formData.emailOrUsername || 'demo@example.com',
      },
    });
    notifyAuthChange();

    router.push('/home');
  };

  // Definisikan transisi untuk KEDUA elemen
  const morphTransition = {
    type: 'spring' as const,
    stiffness: 100,
    damping: 20,
  };

  if (!isReady || isLoggedIn) {
    return <LoadingSpinner label="Memeriksa status login..." />;
  }

  return (
    <div className="auth-figma-page">
      <div className="auth-figma-grid">
        {/* Left side - Form */}
        <motion.div
          className="auth-figma-panel"
          layoutId="form-section"
          transition={morphTransition}
        >
          {/* Kembali ke Beranda Link */}
          <div className="mb-6">
            <Link href="/home" className="auth-figma-back-link">
              <ArrowLeft size={16} />
              Kembali ke Beranda
            </Link>
          </div>

          <div className="auth-figma-heading">
            <h1>Login</h1>
            <p>Masuk untuk melanjutkan perawatan terbaik Anda.</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-figma-form">
            {/* Email/Username Input */}
            <div className="auth-figma-field">
              <div className="auth-figma-field-icon">
                <User size={20} />
              </div>
              <input
                type="text"
                name="emailOrUsername"
                value={formData.emailOrUsername}
                onChange={handleChange}
                placeholder="Masukan email atau username"
                className="auth-figma-input"
                required
              />
            </div>

            {/* Password Input */}
            <div className="auth-figma-field">
              <div className="auth-figma-field-icon">
                <Lock size={20} />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Masukan kata sandi anda"
                className="auth-figma-input auth-figma-input--with-toggle"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="auth-figma-password-toggle"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            {/* Login Button */}
            <button type="submit" className="auth-figma-submit">
              LOGIN
            </button>
          </form>

          {/* Register Link */}
          <div className="auth-figma-switch">
            <p>
              Belum Punya Akun? <Link href="/register">Daftar</Link>
            </p>
          </div>
        </motion.div>

        {/* Right side - Illustration */}
        <motion.div
          className="auth-figma-visual"
          layoutId="image-section"
          transition={morphTransition}
        >
          <img
            src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Image%20Register%20%26%20Login.png-39LkbTrMTCBx60lPiN4zkPodueYnEw.jpeg"
            alt="Beauty workspace illustration"
            className="auth-figma-visual-image"
          />
        </motion.div>
      </div>
    </div>
  );
}
