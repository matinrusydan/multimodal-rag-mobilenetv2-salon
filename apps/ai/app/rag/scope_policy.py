"""Nonclinical and unavailable SOP boundaries, independent of model availability."""
import re


def scope_policy(query):
    text=query.casefold()
    # Mixed business questions continue to retrieval so their factual needs are
    # not silently dropped by an early policy-only response.
    if re.search(r'\b(harga|biaya|tarif|durasi|promo|diskon)\b',text):return None
    if re.search(r'\b(dosis|resep)\b',text) and re.search(r'\b(obat|minum|ketombe|rontok|dokter)\b',text):
        return dict(rule='nonclinical_prescription',reply='TIEN SALON tidak dapat menentukan dosis atau resep obat. Konsultasikan kebutuhan tersebut kepada dokter, dokter spesialis kulit, atau profesional klinis yang berwenang.')
    internal=re.search(r'dipakai|digunakan|pakai apa|produk internal|produk salon',text)
    if re.search(r'merek|merk|brand|produk apa',text) and internal and re.search(r'salon|tien|keratin|smoothing|pewarna',text):
        return dict(rule='confidential_products',reply='Merek dan varian produk internal TIEN SALON tidak dipublikasikan sesuai kebijakan salon. Untuk petunjuk perawatan setelah layanan, silakan konfirmasikan kepada staf yang menangani.')
    if re.search(r'keratin|smoothing',text) and re.search(r'keramas|cuci rambut',text) and re.search(r'kapan|berapa|boleh|hari|jam|setelah|habis',text):
        return dict(rule='unavailable_aftercare_sop',reply='Waktu keramas setelah keratin atau smoothing harus mengikuti instruksi staf yang menangani. Petunjuk khusus layanan TIEN belum tersedia pada sumber chatbot, sehingga saya belum dapat memastikan jeda jam atau harinya. Konfirmasikan kepada staf salon sebelum keramas; jangan menganggap aturan 48 atau 72 jam berlaku untuk semua produk dan layanan.')
    return None
