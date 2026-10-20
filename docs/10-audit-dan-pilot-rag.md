# Audit dan pilot awal penelitian RAG salon

Tanggal: 20 Oktober 2026. Ruang lingkup: RAG, sumber pengetahuan, evaluasi, dan pilot. Tidak mengubah pipeline CV, database bisnis, maupun dokumen LaTeX usulan.

## Hasil yang tersedia

- Snapshot read-only PostgreSQL: enam layanan aktif, diambil `2026-10-20T07:51:39.271Z`; hash record `228719c5239668fe9c7b42dc2ee6b71b83a0954e9034038757100a22dff370ad`.
- Inventaris enam Markdown knowledge base, dengan hash, topik, jumlah chunk dan status sumber.
- Korpus terisolasi 51 evidence: enam record DB dan 45 chunk Markdown. Tidak menulis ke ChromaDB produksi.
- Dataset pilot 24 pertanyaan: masing-masing enam database, dokumen, campuran, dan sulit. Query berupa draft berbantuan asisten yang belum ditinjau peneliti, bukan data pelanggan nyata. Belum menjadi test final.
- Jawaban acuan draft, field bisnis, evidence per kebutuhan, answerability dan lembar anotasi.
- Eksekusi nyata BM25 serta dua kontrol feature hashing tanpa API. Generasi jawaban dan evaluasi faithfulness belum dijalankan.
- Perbaikan ingest dan evaluator beserta tes regresi. Seluruh 45 tes RAG/crawler yang dipilih lulus menggunakan mock, tanpa ChromaDB live atau API model.

Paket data dan hasil berada di [pilot](../apps/ai/rag/eval/pilot/README.md). Dataset yang mudah dibaca tersedia di [questions.md](../apps/ai/rag/eval/pilot/questions.md); detail hasil ada di [retrieval_report.md](../apps/ai/rag/eval/pilot/retrieval_report.md).

## Alur aktif yang ditemukan

`Express /api/chat → FastAPI /ai/chat → RagService.answer → pemilihan mode sumber → embed + retriever atau live web → prompt_builder → Gemini/fallback → respons`.

Chat pelanggan mencari koleksi `RAG_TOPICS`: harga, layanan, gaya-rambut, tips-perawatan, booking-info. Katalog hasil serialisasi database ada pada jalur agent admin; katalog bukan anggota `RAG_TOPICS`. Karena itu keberadaan serializer katalog belum membuktikan bahwa chat pelanggan sudah mendapatkan harga live dari DB.

`classify_topic()` memberi prioritas kuat pada harga/booking, lalu memilih satu topik dominan. Untuk pertanyaan harga plus perawatan, topik harga dapat membatasi pencarian sehingga bukti perawatan terlewat. Ini terbukti sebagai perilaku kode; besar dampaknya pada pengguna nyata belum diukur.

Bila web fallback aktif, deteksi kesehatan dapat memilih web-only dan melewati KB. Dengan demikian, query campuran yang menyebut keluhan belum tentu mendapat fakta layanan/harga. Pilot terisolasi tidak melakukan live web atau membuka browser.

## Temuan dan tindakan

| Temuan | Dampak pada penelitian | Tindakan/status |
|---|---|---|
| API Express/FastAPI tidak menerima koneksi ketika diperiksa | Tidak dapat memperoleh snapshot melalui HTTP | Fallback SELECT langsung PostgreSQL, transaksi read-only repeatable-read; berhasil tanpa menjalankan server/migrasi/seed. |
| Harga Markdown mempunyai promo Rp285.000/Rp690.000; DB hanya mempunyai field `price` | Promo tidak boleh dianggap berlaku hanya karena ditemukan dalam dokumen | Snapshot dipakai untuk nilai field harga; dua query konflik promo dimasukkan. Keberlakuan promo tetap tidak diketahui. |
| Satu file ingest menghapus semua ID lain dalam topik | Bukti file lain dapat hilang dari index saat reingest | Diperbaiki: penghapusan dibatasi prefix nama file saat ini; dua file satu topik serta idempotence diuji. Tidak menjalankan ingest pada index produksi. |
| Metadata asal front-matter hilang pada upsert | Keterlacakan sumber melemah | Metadata source/type/title/tanggal dipertahankan bila tersedia untuk ingest berikutnya. File lama tidak otomatis memperoleh bibliografi yang tidak ada. |
| Evaluator melakukan retrieval sendiri, lalu answer() mengambil ulang konteks | Judge dapat menilai konteks yang berbeda dari sumber jawaban | Evaluator memakai trace dari satu pemanggilan answer(). |
| Prompt memotong KB menjadi 400 karakter dan web 1.100 karakter | Full chunk yang diretrieve belum tentu seluruhnya dilihat generator | Helper pemotongan dipakai bersama oleh prompt dan trace; prompt aktual disimpan untuk evaluasi berizin. |
| Error parsing/judge diperlakukan sebagai nol dan retry menargetkan skor nol | Nol sah tidak dapat dibedakan dari error; retry berpotensi menggeser hasil | Nilai invalid/error menjadi null, nol sah tetap dihitung; retry hanya null, denominator per metrik dilaporkan. |
| Judge berganti model dan generator memakai race beberapa model | Konfigurasi tidak terkendali | Evaluator baru mewajibkan generator dan judge eksplisit; tidak memakai fallback model lain. Runtime publik mempertahankan perilaku semula. |
| Rubrik sendiri diberi nama RAGAS | Klaim metode evaluasi kurang tepat | Disebut custom LLM judge. Hasil baru terpisah dari report `ragas_report*` historis. |
| Gemini embedding bisa fallback ke feature hashing dengan dimensi sama | Dimensi sama tidak berarti ruang embedding sesuai | Ditambahkan strict mode untuk evaluator; query gagal bila provider/key tidak tersedia atau embedding error. Identitas embedding index lama masih perlu diverifikasi. |
| Tidak ditemukan pemeriksaan robots.txt pada jalur crawler yang diperiksa | Akuisisi web belum memenuhi protokol penelitian yang diminta | Tidak melakukan crawl. Gate akuisisi berikutnya: robots, izin akses, sumber dan log tanggal harus tercatat sebelum eksekusi. |
| Markdown perawatan tidak memiliki sumber primer | Tidak layak langsung menjadi gold klinis | Ditandai engineering-only/pending review. Jangan menafsirkan hasil retrieval sebagai validasi saran kesehatan. |

## Hasil pilot yang sudah diukur

Pada BM25 top-k 5, keenam query database dan keenam query dokumen menemukan gold evidence draft masing-masing. Dari enam query campuran, lima mempunyai seluruh kelompok bukti di konteks akhir; satu belum lengkap. Macro recall mixed 0,917 dan F1 retrieval mixed 0,524.

Interpretasi ini dibatasi oleh label draft dan pertanyaan yang disusun langsung dari sumber. Query menyebut nama layanan secara eksplisit sehingga lebih mudah daripada bahasa pelanggan bebas. Bukti relevan alternatif yang belum dilabel dapat mengubah precision/recall. Lima dari enam bukan bukti keunggulan metode usulan, karena metode usulan belum dibandingkan dan belum ada baseline neural dense.

Hash proxy dan hybrid RRF dengan hash proxy mempunyai bukti lengkap pada dua dari enam query campuran. **Jangan menyebutnya hasil dense neural atau bukti hybrid lebih buruk secara umum.** Feature hashing merupakan kontrol leksikal dengan representasi berbeda dari Gemini/SentenceTransformer. Seluruh angka ini hanya diagnosis retrieval engineering.

Tiga kasus ambigu/tidak terjawab tidak mempunyai gold evidence dan tidak masuk denominator retrieval: 21/24 query dinilai untuk retrieval. Ketiganya tetap disimpan dan harus dinilai terpisah untuk abstention/klarifikasi setelah generasi dilakukan. Tidak ada metrik kualitas jawaban yang diganti angka nol atau dikarang.

## Protokol reproduksi dan pengujian

Ekspor snapshot dari root:

```powershell
node apps/api/tools/export_rag_pilot.mjs
```

Pilot dari `apps/ai`:

```powershell
.venv\Scripts\python.exe -m app.rag.pilot --help
.venv\Scripts\python.exe -m app.rag.pilot
.venv\Scripts\python.exe -m app.rag.eval_rag --help
```

Tes yang telah dijalankan dari `apps/ai`:

```powershell
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/test_rag_pilot_protocol.py tests/test_ingest.py tests/test_retriever.py tests/test_antibot.py
```

Tes async Windows sempat tertahan dalam sandbox dan berhasil setelah dijalankan di luar sandbox, tetap dengan mock. Dua proses bantuan CLI yang tertahan dihentikan. CLI --help diperbaiki agar parsing argumen berlangsung sebelum event loop dibuat.

Tidak ada migrasi, seed, lint, pemanggilan API LLM/embedding, eksekusi crawler/browser, atau perubahan kredensial. Git diperiksa dengan safe.directory per-command; konfigurasi global Git tidak diubah. Perubahan pengguna yang sudah ada pada `.gitignore`, direktori CV, artikel dan output dipertahankan.

## Yang belum selesai dan keputusan berikutnya

1. **Validasi anotasi 24 item.** Pengguna/pemeriksa meninjau referensi, seluruh kelompok bukti dan bukti alternatif. Catat reviewer, keputusan dan alasan. Tidak ada inter-annotator agreement sampai tersedia dua penilai.
2. **Konfirmasi data bisnis.** Snapshot menyatakan isi DB lokal, bukan verifikasi pemilik salon. Arti harga, promo, durasi dan kebijakan perlu konfirmasi sebelum klaim tentang layanan nyata.
3. **Kurasi dokumen perawatan.** Gunakan sumber yang sesuai dan berprovenance. Materi manual lama tetap menjadi fixture diagnosis engineering, bukan jawaban klinis final.
4. **Baseline neural dense dan hybrid sesungguhnya.** Bangun index terisolasi dengan embedding tetap dan identitas model yang tercatat, setelah biaya/perangkat dan korpus siap. Jangan mencampur fallback hashing ke index Gemini.
5. **Pilot generation dan anotasi jawaban.** Gunakan generator tetap, konteks aktual, rubrik yang jelas; ukur fakta bisnis, claim support, sitasi, abstention dan latensi. Evaluator API baru bersifat opsional dan belum dijalankan. Hasilnya tidak otomatis ilmiah hanya karena berupa skor LLM judge.
6. **Kunci intervensi dan novelty.** Gunakan error pilot untuk menentukan apakah source routing benar diperlukan, dan cari studi paling dekat sebelum menyatakan kontribusi baru. Jangan langsung menambah graf/agent/reranker tanpa bukti kebutuhan.

Fase audit dan pilot retrieval awal telah dilakukan. Program RAG publik belum dinyatakan selesai atau sudah terintegrasi database live; fase intervensi dan evaluasi jawaban menunggu validasi sumber serta baseline yang sesuai.
