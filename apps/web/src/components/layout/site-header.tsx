'use client';

import { BrandLogo } from '@/components/brand/brand-logo';
import { Button } from '@/components/ui/button';
import { NAV_ITEMS } from '@/lib/constants';
import { useAuth } from '@/lib/use-auth';
import { cn } from '@/lib/utils';
import { Menu, X } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

export type NavItem = {
  label: string;
  href: string;
};

type SiteHeaderProps = {
  className?: string;
};

export function SiteHeader({ className }: SiteHeaderProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, isLoggedIn, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);

  const isAdmin =
    user?.type === 0 ||
    ['users', 'roles', 'permissions', 'routes', 'menus'].some((resource) =>
      user?.permissions?.includes(`${resource}.read`),
    );

  const handleLogout = () => {
    logout();
    setIsOpen(false);
    router.push('/home');
  };

  const renderLinks = (isMobile = false) => (
    <>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={cn('site-header__link', pathname === item.href && 'site-header__link--active')}
          onClick={() => isMobile && setIsOpen(false)}
        >
          {item.label}
        </Link>
      ))}
    </>
  );

  return (
    <header className={cn('site-header', className)}>
      <div className="site-container site-header__inner">
        <BrandLogo href="/home" />
        <nav className="site-header__nav" aria-label="Navigasi utama">
          {renderLinks()}
        </nav>
        <div className="site-header__actions">
          {isLoggedIn ? (
            <>
              <Button href="/reservation" size="sm">
                Reservasi
              </Button>
              {isAdmin ? (
                <Button href="/admin" variant="outline" size="sm">
                  Admin
                </Button>
              ) : null}
              <span className="site-header__greeting">Halo, {user?.name}</span>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                Keluar
              </Button>
            </>
          ) : (
            <>
              <a href="/auth" className="site-header__auth-link">
                Masuk
              </a>
              <a
                href="/auth?mode=register"
                className="site-header__auth-link site-header__auth-link--primary"
              >
                Daftar
              </a>
            </>
          )}
        </div>
        <button
          className="site-header__menu-button"
          type="button"
          aria-label={isOpen ? 'Tutup menu' : 'Buka menu'}
          aria-expanded={isOpen}
          onClick={() => setIsOpen((current) => !current)}
        >
          {isOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
      {isOpen ? (
        <div className="site-header__mobile-panel">
          <nav className="site-container site-header__mobile-nav" aria-label="Navigasi mobile">
            {renderLinks(true)}
            {isLoggedIn ? (
              <>
                <Button href="/reservation" onClick={() => setIsOpen(false)}>
                  Reservasi
                </Button>
                {isAdmin ? (
                  <Button href="/admin" onClick={() => setIsOpen(false)}>
                    Admin
                  </Button>
                ) : null}
                <span className="site-header__greeting">Halo, {user?.name}</span>
                <Button variant="outline" onClick={handleLogout}>
                  Keluar
                </Button>
              </>
            ) : (
              <>
                <a href="/auth" className="site-header__auth-link" onClick={() => setIsOpen(false)}>
                  Masuk
                </a>
                <a
                  href="/auth?mode=register"
                  className="site-header__auth-link site-header__auth-link--primary"
                  onClick={() => setIsOpen(false)}
                >
                  Daftar
                </a>
              </>
            )}
          </nav>
        </div>
      ) : null}
    </header>
  );
}
