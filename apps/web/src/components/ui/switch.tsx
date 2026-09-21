'use client';

import * as SwitchPrimitive from '@radix-ui/react-switch';

type SwitchProps = {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  onLabel?: string;
  offLabel?: string;
};

export function Switch({ checked, onCheckedChange, onLabel = 'Ya', offLabel = 'Tidak' }: SwitchProps) {
  return (
    <div className="admin-switch">
      <SwitchPrimitive.Root
        checked={checked}
        onCheckedChange={onCheckedChange}
        className="admin-switch__root"
      >
        <SwitchPrimitive.Thumb className="admin-switch__thumb" />
      </SwitchPrimitive.Root>
      <span className="admin-switch__label">{checked ? onLabel : offLabel}</span>
    </div>
  );
}
