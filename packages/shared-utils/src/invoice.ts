/** Generate nomor invoice: INV-YYYYMMDD-XXX */
export function generateInvoiceNumber(seq: number, date = new Date()): string {
  const yyyy = date.getFullYear();
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  const padded = String(seq).padStart(3, '0');
  return `INV-${yyyy}${mm}${dd}-${padded}`;
}

/** Generate id sederhana untuk payment: PAY-XXXXXX */
export function generatePaymentId(): string {
  const rand = Math.floor(100000 + Math.random() * 900000);
  return `PAY-${rand}`;
}
