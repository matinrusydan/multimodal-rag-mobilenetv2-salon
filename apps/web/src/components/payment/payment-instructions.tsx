import type { PaymentMethodId } from '@/components/payment/payment-method';

const instructions: Record<PaymentMethodId, string[]> = {
  qris: [
    'Buka aplikasi pembayaran.',
    'Scan QRIS dummy di halaman ini.',
    'Klik tombol simulasi berhasil.',
  ],
  virtual_account: [
    'Pilih transfer virtual account.',
    'Masukkan BCA VA 1234567890123.',
    'Konfirmasi pembayaran demo.',
  ],
  ewallet: [
    'Pilih GoPay, OVO, atau Dana.',
    'Gunakan nomor dummy 081234567890.',
    'Selesaikan simulasi pembayaran.',
  ],
  bank_transfer: [
    'Transfer ke BCA 123-456-7890.',
    'Nama rekening TIEN SALON.',
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
