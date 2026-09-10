import type { PaymentMethodId } from '@/components/payment/payment-method';

const instructions: Record<PaymentMethodId, string[]> = {
  qris: [
    'Buka aplikasi pembayaran.',
    'Scan QRIS dummy di halaman ini.',
    'Klik tombol simulasi berhasil.',
  ],
  transfer: [
    'Transfer ke BCA 123-456-7890.',
    'Nama rekening TIEN SALON.',
    'Klik simulasi berhasil setelah membaca instruksi.',
  ],
  cash: [
    'Siapkan nominal tunai sesuai total.',
    'Bayar langsung di kasir salon.',
    'Klik simulasi berhasil setelah membaca instruksi.',
  ],
};

type PaymentInstructionsProps = {
  method: PaymentMethodId;
};

export function PaymentInstructions({ method }: PaymentInstructionsProps) {
  return (
    <div className="payment-instructions">
      <h2>Instruksi Pembayaran Dummy</h2>
      <ol>
        {instructions[method].map((instruction) => (
          <li key={instruction}>{instruction}</li>
        ))}
      </ol>
    </div>
  );
}
