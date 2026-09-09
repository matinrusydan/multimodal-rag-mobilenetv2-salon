'use client';

import { motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, Lock, Mail, User } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type React from 'react';
import { useEffect, useState } from 'react';

import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SESSION_KEYS } from '@/lib/constants';
import { writeSession } from '@/lib/session';
import { notifyAuthChange, useAuth } from '@/lib/use-auth';

export default function RegisterPage() {
  const router = useRouter();
  const { isLoggedIn, isReady } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [error, setError] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
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

    if (formData.password !== formData.confirmPassword) {
      setError('Password dan konfirmasi password harus cocok.');
      return;
    }

    writeSession(SESSION_KEYS.auth, {
      isLoggedIn: true,
      user: {
        name: formData.username || 'Pelanggan Demo',
        email: formData.email || 'demo@example.com',
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
        {/* Left side - Illustration */}
        <motion.div
          className="auth-figma-visual order-first"
          layoutId="image-section"
          transition={morphTransition}
        >
          <img
            src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Image%20Register%20%26%20Login.png-39LkbTrMTCBx60lPiN4zkPodueYnEw.jpeg"
            alt="Beauty workspace illustration"
            className="auth-figma-visual-image"
          />
        </motion.div>

        {/* Right side - Form */}
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
            <h1>Daftar</h1>
            <p>Daftar sekarang untuk menikmati layanan perawatan terbaik kami!</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-figma-form">
            {/* Email Input */}
            <div className="auth-figma-field">
              <div className="auth-figma-field-icon">
                <Mail size={20} />
              </div>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="Masukkan email anda"
                required
                className="auth-figma-input"
              />
            </div>

            {/* Username Input */}
            <div className="auth-figma-field">
              <div className="auth-figma-field-icon">
                <User size={20} />
              </div>
              <input
                type="text"
                name="username"
                value={formData.username}
                onChange={handleChange}
                placeholder="Masukkan username anda"
                required
                className="auth-figma-input"
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
                placeholder="Masukkan kata sandi anda"
                required
                className="auth-figma-input auth-figma-input--with-toggle"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="auth-figma-password-toggle"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            {/* Confirm Password Input */}
            <div className="auth-figma-field">
              <div className="auth-figma-field-icon">
                <Lock size={20} />
              </div>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                name="confirmPassword"
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="Konfirmasi kata sandi anda"
                required
                className="auth-figma-input auth-figma-input--with-toggle"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="auth-figma-password-toggle"
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>

            {error && <p className="text-red-500 text-sm font-semibold mt-1">{error}</p>}

            {/* Register Button */}
            <button type="submit" className="auth-figma-submit">
              DAFTAR
            </button>
          </form>

          {/* Login Link */}
          <div className="auth-figma-switch">
            <p>
              Sudah Punya Akun? <Link href="/login">Masuk</Link>
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
