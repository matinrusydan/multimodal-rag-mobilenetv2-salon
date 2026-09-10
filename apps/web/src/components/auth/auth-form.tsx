'use client';

import { AnimatePresence, motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, User } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import type React from 'react';
import { useState } from 'react';

import { notifyAuthChange } from '@/lib/use-auth';

export type AuthMode = 'login' | 'register';

const CONTENT: Record<AuthMode, { title: string; subtitle: string; submitLabel: string }> = {
  login: {
    title: 'Login',
    subtitle: 'Masuk untuk melanjutkan perawatan terbaik Anda.',
    submitLabel: 'LOGIN',
  },
  register: {
    title: 'Daftar',
    subtitle: 'Daftar sekarang untuk menikmati layanan perawatan terbaik kami!',
    submitLabel: 'DAFTAR',
  },
};

type AuthFormProps = {
  mode: AuthMode;
  redirect?: string;
};

const fieldMotion = {
  initial: { opacity: 0, y: -8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.22 },
};

export function AuthForm({ mode, redirect }: AuthFormProps) {
  const router = useRouter();
  const isRegister = mode === 'register';
  const content = CONTENT[mode];

  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState({
    emailOrUsername: '',
    email: '',
    name: '',
    password: '',
    confirmPassword: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (isRegister && data.password !== data.confirmPassword) {
      setError('Password dan konfirmasi password harus cocok.');
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = isRegister
        ? { name: data.name, email: data.email, password: data.password }
        : { email: data.emailOrUsername, password: data.password };

      const res = await fetch(isRegister ? '/api/auth/register' : '/api/auth/login', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const body = (await res.json().catch(() => null)) as {
          detail?: string;
          title?: string;
        } | null;
        setError(body?.detail ?? body?.title ?? 'Gagal memproses. Silakan coba lagi.');
        return;
      }

      notifyAuthChange();
      router.push(redirect || '/home');
    } catch {
      setError('Terjadi kesalahan jaringan. Silakan coba lagi.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="auth-figma-heading" key={`heading-${mode}`}>
        <h1>{content.title}</h1>
        <p>{content.subtitle}</p>
      </div>

      <form onSubmit={handleSubmit} className="auth-figma-form">
        <AnimatePresence initial={false} mode="popLayout">
          {isRegister ? (
            <>
              <motion.div key="name" className="auth-figma-field" {...fieldMotion}>
                <div className="auth-figma-field-icon">
                  <User size={20} />
                </div>
                <input
                  type="text"
                  name="name"
                  value={data.name}
                  onChange={handleChange}
                  placeholder="Masukkan username anda"
                  className="auth-figma-input"
                  required
                />
              </motion.div>
              <motion.div key="email" className="auth-figma-field" {...fieldMotion}>
                <div className="auth-figma-field-icon">
                  <Mail size={20} />
                </div>
                <input
                  type="email"
                  name="email"
                  value={data.email}
                  onChange={handleChange}
                  placeholder="Masukkan email anda"
                  className="auth-figma-input"
                  required
                />
              </motion.div>
            </>
          ) : (
            <motion.div key="emailOrUsername" className="auth-figma-field" {...fieldMotion}>
              <div className="auth-figma-field-icon">
                <User size={20} />
              </div>
              <input
                type="text"
                name="emailOrUsername"
                value={data.emailOrUsername}
                onChange={handleChange}
                placeholder="Masukan email atau username"
                className="auth-figma-input"
                required
              />
            </motion.div>
          )}

          <motion.div key="password" className="auth-figma-field" {...fieldMotion}>
            <div className="auth-figma-field-icon">
              <Lock size={20} />
            </div>
            <input
              type={showPassword ? 'text' : 'password'}
              name="password"
              value={data.password}
              onChange={handleChange}
              placeholder="Masukkan kata sandi anda"
              className="auth-figma-input auth-figma-input--with-toggle"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
              className="auth-figma-password-toggle"
            >
              {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
            </button>
          </motion.div>

          {isRegister ? (
            <motion.div key="confirmPassword" className="auth-figma-field" {...fieldMotion}>
              <div className="auth-figma-field-icon">
                <Lock size={20} />
              </div>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                name="confirmPassword"
                value={data.confirmPassword}
                onChange={handleChange}
                placeholder="Konfirmasi kata sandi anda"
                className="auth-figma-input auth-figma-input--with-toggle"
                required
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((current) => !current)}
                className="auth-figma-password-toggle"
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {error && <p className="text-red-500 text-sm font-semibold mt-1">{error}</p>}

        <button type="submit" className="auth-figma-submit" disabled={isSubmitting}>
          {isSubmitting ? 'MEMPROSES...' : content.submitLabel}
        </button>
      </form>

      <div className="auth-figma-switch">
        {isRegister ? (
          <p>
            Sudah Punya Akun? <Link href="/auth">Masuk</Link>
          </p>
        ) : (
          <p>
            Belum Punya Akun? <Link href="/auth?mode=register">Daftar</Link>
          </p>
        )}
      </div>
    </>
  );
}
