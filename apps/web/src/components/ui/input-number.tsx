'use client';

type InputNumberProps = {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  id?: string;
};

export function InputNumber({ value, onChange, min = 0, max = 9999, id }: InputNumberProps) {
  const clamp = (n: number) => Math.max(min, Math.min(max, n));
  return (
    <div className="admin-inputnumber">
      <input
        id={id}
        type="number"
        className="admin-inputnumber__input"
        value={Number.isFinite(value) ? value : 0}
        min={min}
        max={max}
        onChange={(e) => onChange(clamp(Number(e.target.value)))}
      />
      <div className="admin-inputnumber__actions">
        <button type="button" aria-label="Tambah" onClick={() => onChange(clamp(value + 1))}>
          +
        </button>
        <button type="button" aria-label="Kurangi" onClick={() => onChange(clamp(value - 1))}>
          −
        </button>
      </div>
    </div>
  );
}
