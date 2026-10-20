# Protokol dan anotasi IR v1

Status: persiapan eksperimen, belum test set independen. Seluruh file template masih pending.

1. Di `answer-review.template.json`, periksa pertanyaan, acuan baru dan evidence. Usulan field bukan daftar wajib final: pilih field yang benar-benar diminta. Rekam persetujuan acuan terpisah dari penilaian jawaban.
2. Simpan jawaban sistem yang sebenarnya di `answer`, asal/versi di `answer_source`. Isi field yang disebut, klaim, sitasi, kebutuhan jawaban dan pemeriksaan kebijakan. Nilai true/false/null; null berarti belum dinilai. Set reviewer, tanggal dan approved hanya setelah selesai.
3. `context-review.template.json` berisi cuplikan yang benar-benar digunakan pada eksperimen. Periksa apakah setiap kebutuhan masih memiliki teks pendukung setelah pemotongan. Ini belum penilaian otomatis kualitas bukti.
4. Tetapkan keluarga skenario pada `split-review.template.json`. Dua parafrasa dari kebutuhan sama tidak boleh dipisahkan ke development/test. Dua belas kandidat tambahan masih draft, bukan test yang siap diuji. Tinjau acuan, bukti, overlap, lalu bekukan test. Pertanyaan yang sudah dipakai menyetel sistem tetap development.
5. Jangan menimpa template/hasil beku: simpan salinan bernomor untuk review yang sudah diisi.

Perintah dari `apps/ai`:

```powershell
.\.venv\Scripts\python.exe -m app.rag.split_guard --input rag/eval/ir-protocol-v1/split-review.template.json --require-locked-test
.\.venv\Scripts\python.exe -m app.rag.answer_audit --annotations rag/eval/ir-protocol-v1/answer-review.template.json --out rag/eval/ir-protocol-v1/answer-review-status.json
```

Validasi split saat ini sengaja menghasilkan `not_ready` (exit 2), karena keluarga dan pemeriksa belum diisi. Audit template menghasilkan 0 jawaban dinilai, bukan skor kualitas nol atau sempurna. Pemeriksa tunggal dinyatakan sebagai keterbatasan; tidak ada klaim kesepakatan antarpenilai.
