'use client';

import * as Popover from '@radix-ui/react-popover';
import { Check, ChevronDown } from 'lucide-react';
import { useState } from 'react';

export type MultiOption = { value: string; label: string };

type MultiSelectProps = {
  values: string[];
  options: MultiOption[];
  onChange: (values: string[]) => void;
  placeholder?: string;
};

export function MultiSelect({ values, options, onChange, placeholder = 'Pilih...' }: MultiSelectProps) {
  const [open, setOpen] = useState(false);

  const toggle = (value: string) => {
    if (values.includes(value)) {
      onChange(values.filter((v) => v !== value));
    } else {
      onChange([...values, value]);
    }
  };

  const labelByValue = new Map(options.map((o) => [o.value, o.label]));
  const selectedLabels = values.map((v) => labelByValue.get(v) ?? v);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className="admin-select__trigger" type="button">
        <span className={selectedLabels.length ? 'admin-multiselect__value' : 'admin-select__placeholder'}>
          {selectedLabels.length ? selectedLabels.join(', ') : placeholder}
        </span>
        <ChevronDown size={16} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="admin-multiselect__content" sideOffset={4} align="start">
          <div className="admin-multiselect__list">
            {options.map((opt) => {
              const active = values.includes(opt.value);
              return (
                <button
                  key={opt.value}
                  type="button"
                  className="admin-multiselect__option"
                  onClick={() => toggle(opt.value)}
                >
                  <span className={active ? 'admin-checkbox admin-checkbox--checked' : 'admin-checkbox'}>
                    {active ? <Check size={12} /> : null}
                  </span>
                  {opt.label}
                </button>
              );
            })}
            {options.length === 0 ? <span className="muted-text">Tidak ada pilihan.</span> : null}
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
