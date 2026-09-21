'use client';

import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import type React from 'react';

import { cn } from '@/lib/utils';

type ModalProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  className?: string;
};

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  className,
}: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="admin-modal__overlay" />
        <Dialog.Content className={cn('admin-modal__content', className)}>
          <div className="admin-modal__header">
            <Dialog.Title className="admin-modal__title">{title}</Dialog.Title>
            <Dialog.Close className="admin-modal__close" aria-label="Tutup">
              <X size={18} />
            </Dialog.Close>
          </div>
          <Dialog.Description className="admin-modal__desc">
            {description ?? title}
          </Dialog.Description>
          <div className="admin-modal__body">{children}</div>
          {footer ? <div className="admin-modal__footer">{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
