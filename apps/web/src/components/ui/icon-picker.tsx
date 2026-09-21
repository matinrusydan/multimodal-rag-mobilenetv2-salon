'use client';

import * as Popover from '@radix-ui/react-popover';
import { ChevronDown, Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import { ADMIN_ICONS, ADMIN_ICON_NAMES, getAdminIcon } from '@/lib/admin-icons';

type IconPickerProps = {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
};

export function IconPicker({ value, onValueChange, placeholder = 'Pilih icon' }: IconPickerProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return ADMIN_ICON_NAMES.filter((n) => (q ? n.includes(q) : true));
  }, [query]);

  const Selected = getAdminIcon(value);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className="admin-select__trigger" type="button">
        <span className="admin-iconpicker__current">
          <Selected size={16} />
          <span>{value || placeholder}</span>
        </span>
        <ChevronDown size={16} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="admin-iconpicker__content" sideOffset={4} align="start">
          <div className="admin-iconpicker__search">
            <Search size={14} />
            <input
              type="text"
              placeholder="Cari icon..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div className="admin-iconpicker__grid">
            {filtered.map((name) => {
              const Icon = ADMIN_ICONS[name];
              return (
                <button
                  key={name}
                  type="button"
                  className={
                    name === value
                      ? 'admin-iconpicker__cell admin-iconpicker__cell--active'
                      : 'admin-iconpicker__cell'
                  }
                  title={name}
                  onClick={() => {
                    onValueChange(name);
                    setOpen(false);
                  }}
                >
                  <Icon size={18} />
                  <span>{name}</span>
                </button>
              );
            })}
            {filtered.length === 0 ? <span className="muted-text">Tidak ditemukan.</span> : null}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
