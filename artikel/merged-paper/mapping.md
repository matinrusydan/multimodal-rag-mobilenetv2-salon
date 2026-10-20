# Mapping 25 paper untuk penelitian RAG salon

Tanggal penyusunan: 20 Oktober 2026. Objek rencana penelitian: konsultasi salon berbahasa Indonesia yang menggunakan database sebagai sumber fakta layanan/harga dan dokumen sebagai sumber pengetahuan perawatan. Batas tahun koleksi: 2021–2026.

## 1. Cakupan dan cara membaca

Mapping mencakup **25 PDF yang tersedia di folder ini**, terdiri dari 19 PDF hasil unduhan dan enam PDF pengguna hasil seleksi awal. Nama PDF tidak diubah. Nomor P01–P25 di laporan ini adalah urutan prioritas relevansi, bukan nomor pada nama PDF lama.

Dasar pemetaan adalah pembacaan bagian relevan dari teks PDF: abstrak, metode, sumber data, evaluasi, hasil, dan keterbatasan/simpulan. Beberapa tabel diperiksa secara visual untuk mengonfirmasi angka dan perbedaan pelaporannya. Ini merupakan kajian terarah atas koleksi lokal, **bukan systematic literature review yang menjamin cakupan seluruh penelitian di dunia**. Tidak seluruh referensi yang dikutip oleh masing-masing paper sudah diverifikasi kembali, dan eksperimennya belum direplikasi.

Hasil numerik di bawah adalah **hasil yang dilaporkan penulis paper**, bukan hasil eksperimen proyek RAG salon. Angka dari dataset, bahasa, generator, dan protokol berbeda tidak boleh dipakai sebagai leaderboard lintas-paper.

Ranking dibuat secara ordinal dengan urutan pertimbangan: (1) kedekatan dengan integrasi informasi operasional dan dokumen; (2) kegunaan metode untuk retrieval/konsultasi salon; (3) kegunaan desain data dan evaluasi; (4) dukungan terhadap objek salon/perawatan. Ranking ini adalah keputusan kajian, bukan skor bibliometrik atau penilaian mutu jurnal. Paper yang paling dekat secara topik tetap dapat mempunyai kelemahan bukti yang serius.

## 2. Panduan penulisan yang diterapkan

| Materi panduan | Halaman PDF rujukan | Penerapan pada mapping |
|---|---|---|
| Bagian Judul dan Afiliasi Naskah | 3–6 | Judul harus spesifik, mencerminkan metode, tujuan, objek, serta konsisten dengan hasil. Judul final ditetapkan setelah desain dan temuan jelas. |
| Bagian Abstrak dan Kata Kunci | 3–6 | Abstrak memuat latar, masalah, metode, hasil numerik, dan simpulan; disusun setelah penelitian selesai. |
| Bagian Pendahuluan dan Pekerjaan Terkait | 7–10 | Alur OMKKMasaSolTu: objek, metode yang ada, kelebihan/kekurangan, masalah metode, solusi, tujuan; RP–RQ–RO harus selaras. |
| Bagian Pendahuluan dan Pekerjaan Terkait | 18–19 | Telaah kritis dengan format masalah–metode–hasil, diikuti tabel state-of-the-art dan penjelasan posisi penelitian. |
| Bagian Tubuh Utama Naskah (HDP) | 5–8, 12–13 | Jelaskan pengumpulan data, pengolahan awal, metode, eksperimen, evaluasi, dan ancaman validitas; pengukuran harus sesuai masalah. |
| Bagian Kesimpulan | 3–4 | Simpulan menjawab rumusan masalah dan tujuan; generalisasi dibatasi bukti, keterbatasan, dan cakupan eksperimen. |

Sumber panduan berada di `C:/Users/lilol/Documents/Penelitian Ilmiah`. Nomor halaman dalam laporan ini selalu **halaman PDF mulai dari 1**, sehingga dapat berbeda dari nomor halaman jurnal atau nomor slide.

## 3. Tabel state-of-the-art dan ranking relevansi

| Rank/ID | Penulis; tahun | Paper / fokus | Masalah | Metode | Hasil utama yang dilaporkan | Peran untuk penelitian |
|---|---|---|---|---|---|---|
| 01 / P01 | Burbano dkk.; 2026 | [RAG chatbot with structured database access][P01] | Akses informasi operasional toko melalui bahasa alami | Mistral-7B, SQL, FAISS, sinkronisasi database | Empat skor evaluasi masing-masing 0,80; pelaporan statistik/waktu perlu dikritisi | Paling dekat untuk arsitektur sumber operasional; bukti hasil perlu kehati-hatian tinggi |
| 02 / P02 | Hsueh & Lin; 2026 | [Customer service RAG + knowledge graph][P02] | Jawaban layanan pelanggan membutuhkan relasi lintas dokumen dan aturan | RAG + Neo4j + QA terkurasi + penilaian GPT | Skor GPT 28,65 → 31,81 → 34,58 untuk LLM-only, RAG-only, RAG+KG | Pembanding integrasi bukti dan konflik kemutakhiran |
| 03 / P03 | Cruz dkk.; 2025 | [Lisa: a touristic chatbot for Lisbon][P03] | Informasi layanan tersebar di banyak website | Web scraping, preprocessing, dense/BM25/hybrid RRF | SAS hybrid 56,66%; setelah preprocessing 65,73% pada kondisi terkait | Contoh akuisisi web, cleaning, baseline, dan evaluasi kebutuhan pengguna |
| 04 / P04 | Khasanova Zafar kizi & Suh; 2025 | [RAG pipelines for international student admissions][P04] | Informasi layanan tersebar dalam panduan dan FAQ | Variasi chunking, dense/MMR/hybrid/multiquery, model lokal dan komersial | OpenChat hybrid unggul pada beberapa konfigurasi; latensi menjadi trade-off | Acuan eksperimen retrieval dan evaluasi dua jenis referensi |
| 05 / P05 | Salman dkk.; 2026 | [Campus service and information chatbot][P05] | LLM menghasilkan informasi kampus yang tidak didukung sumber | multilingual-e5, BM25, RRF, cross-encoder, LLaMA | Tabel perbandingan: P@3 71,7%; R@3 87,5%; F1@3 78,8%; faithfulness hybrid 88,8% | Pembanding retrieval berbahasa Indonesia; bukan kebaruan baru untuk sekadar hybrid |
| 06 / P06 | Byun dkk.; 2024 | [RAG for personalized databases][P06] | Jawaban umum tidak mencerminkan dokumen personal | Tagging dokumen, SQL, ChromaDB, riwayat MongoDB, beberapa LLM/embedding | Pada commonsense: faithfulness 0,51 dan answer relevancy 0,86 untuk konfigurasi terpilih | Pengelolaan dokumen personal dan pemisahan dimensi evaluasi |
| 07 / P07 | Topić dkk.; 2026 | [RAG for soil science question answering][P07] | Pilihan chunking, embedding, retrieval belum jelas pada korpus ilmiah berbeda | Eksperimen komponen bertahap pada tiga korpus | Hybrid RRF recall@5 0,957; 0,960; 0,647 menurut korpus | Acuan preprocessing PDF, provenance, dan batas interpretasi retrieval |
| 08 / P08 | Yang dkk.; 2026 | [Evaluation-guided RAG optimization in oil and gas][P08] | Salah retrieval, angka/entitas, kemutakhiran, dan jawaban tanpa bukti | DAAE, deterministic metrics + judge, hybrid/reranking/metadata | Hit@5 87/150 → 134/150; faithfulness 0,65 → 0,94 | Acuan evaluasi angka, data mutakhir, error, dan optimasi berbasis diagnosis |
| 09 / P09 | Knollmeyer dkk.; 2026 | [Review of RAG evaluation dimensions][P09] | Metrik dipilih tanpa hubungan jelas dengan data dan jenis pertanyaan | SLR 12 studi; matriks dimensi–metrik–evaluator | Kerangka multidimensi; bukan hasil peningkatan satu algoritma | Dasar memilih parameter uji dan data referensi |
| 10 / P10 | Es dkk.; 2024 | [RAGAS][P10] | Evaluasi pipeline membutuhkan ukuran grounding, relevansi jawaban, dan konteks | Evaluasi berbasis LLM, dekomposisi klaim, rekonstruksi pertanyaan | Agreement dengan manusia: 0,95; 0,78; 0,70 untuk tiga dimensi | Sumber primer definisi evaluasi; prosiding terbit |
| 11 / P11 | Gao dkk.; 2023 | [Enabling LLMs to generate text with citations][P11] | Jawaban lancar belum tentu benar atau didukung sitasi | ALCE, retrieval + generasi bersitasi, evaluasi entailment | Sekitar separuh generasi baseline ELI5 belum sepenuhnya didukung sitasi | Dasar evaluasi ketepatan dan kelengkapan dukungan sitasi; prosiding terbit |
| 12 / P12 | Lee & Choi; 2026 | [TechDocRAG][P12] | Pemotongan dokumen menghilangkan hubungan bukti | Graf elemen, identifier–summary–raw evidence, evidence bundling | Strict raw evidence hit rate 0,510 → 0,942 pada subset beranotasi | Konsep pemeliharaan relasi bukti; implementasi cukup kompleks |
| 13 / P13 | Gao, He & Zhang; 2026 | [SES-RAG][P13] | Chunk terputus, query–document mismatch, dan konteks bising | ModernBERT segmentation, GAQE, adaptive context truncation | QASPER F1-Match 37,23 → 41,06 dibanding naive | Kandidat kajian seleksi konteks; biaya/training perlu dinilai |
| 14 / P14 | Putro dkk.; 2025 | [RAG chatbot for energy-sector complaints][P14] | Informasi keluhan internal dan variasi bahasa Indonesia | Narasi dari data internal, FAISS, LLM lokal, klarifikasi/fallback | BLEU-4 46,5; ROUGE-L 0,63; helpfulness 92% | Aplikasi layanan pelanggan Indonesia; skala evaluasi sangat kecil |
| 15 / P15 | Jiang dkk.; 2026 | [Dual-index RAG for mathematics][P15] | Retrieval melewatkan struktur dan mengambil contoh mirip tetapi keliru | ChromaDB + NetworkX, hybrid, filtering | Recall@10 0,058 → 0,181; filter tidak menambah hasil agregat | Contoh penting hasil negatif dan ablation yang jujur |
| 16 / P16 | Klesel & Wittmann; 2025 | [Retrieval-Augmented Generation][P16] | Organisasi membutuhkan pengetahuan yang tidak tersimpan dalam LLM | Artikel konseptual arsitektur, manfaat, tantangan | Sintesis konseptual; tidak ada skor eksperimen salon | Landasan teori yang terbit 2025 |
| 17 / P17 | Wu dkk.; 2026 | [RAG for NLP: a survey][P17] | Ragam retriever dan mekanisme fusion sulit diposisikan | Survei dan taksonomi retrieval fusion | Pemetaan query/logits/latent/parametric fusion dan tantangan | Sumber untuk penelusuran metode primer lanjutan |
| 18 / P18 | Ghaywat dkk.; 2026 | [Survey of conversational AI and RAG chatbots][P18] | Kegagalan chatbot dipengaruhi interaksi komponen | Survei arsitektur dari chunking sampai attribution/evaluation | Sintesis desain dan trade-off; bukan benchmark tunggal | Peta arsitektur dan pemeriksaan kelengkapan desain |
| 19 / P19 | Abo El-Enen, Saad & Nazmy; 2025 | [Survey of RAG for healthcare][P19] | Pengetahuan khusus perlu bukti, kemutakhiran, dan transparansi | Survei Naive/Advanced/Modular RAG dan aplikasi kesehatan | Sintesis lintas studi; skor yang dikutip berasal dari studi berbeda | Konteks sumber perawatan berbukti; bukan pedoman terapi |
| 20 / P20 | Rachmawati dkk.; 2025 | [Kepuasan pelanggan salon][P20] | Hubungan layanan, produk, harga, dan kepuasan salon | Survei 100 pelanggan, regresi linier berganda | Hubungan signifikan dilaporkan untuk ketiga variabel | Pendukung objek salon; tidak membuktikan manfaat chatbot |
| 21 / P21 | Amelia Putri dkk.; 2026 | [Sistem informasi Annisavy][P21] | Pengelolaan pemesanan dan transaksi jasa kecantikan | Waterfall, wawancara/observasi, black-box | Fungsi layanan/pemesanan/laporan berjalan pada pengujian akhir | Pembanding aplikasi jasa kecantikan |
| 22 / P22 | Prayogo dkk.; 2024 | [Pengetahuan dan penanganan ketombe][P22] | Pengetahuan belum selalu sejalan dengan tindakan/pemilihan produk | Survei deskriptif 161 mahasiswi | 139 pernah berketombe; tabel tindakan masih menunjukkan banyak tindakan kurang tepat | Bukti terbatas kebutuhan informasi perawatan |
| 23 / P23 | Mali dkk.; 2025 | [3D hairstyle recommendation and salon scheduling][P23] | Reservasi dan visualisasi gaya rambut terpisah | Aplikasi booking, rekomendasi, visualisasi 3D | Integrasi fungsi dan hasil implementasi dilaporkan | Pendukung aplikasi salon; prosiding, bukan baseline RAG |
| 24 / P24 | Agriani dkk.; 2026 | [Factors related to pityriasis capitis][P24] | Faktor yang berkaitan dengan kejadian ketombe pada populasi khusus | Cross-sectional, 199 mahasiswi, Chi-square | Asosiasi faktor pemakaian jilbab/perawatan dengan ketombe dilaporkan | Opsional jika ketombe masuk ruang lingkup |
| 25 / P25 | Horas dkk.; 2026 | [Strategi industri kecantikan Indonesia][P25] | Faktor strategis pengembangan industri kecantikan | Data sekunder, Porter Diamond, SWOT/TOWS | Sintesis kekuatan, kelemahan, peluang, ancaman, dan strategi | Konteks industri luas; relevansi metode RAG rendah |

## 4. Mapping kritis per paper

### P01 — Design and Evaluation of a Retrieval-Augmented Generation LLM Chatbot with Structured Database Access

- **Identitas:** Burbano dkk., 2026; Applied Sciences; DOI `10.3390/app16073147`. [PDF][P01].
- **Masalah dan metode:** Akses informasi produk, harga, persediaan, dan operasional toko melalui percakapan. Menggabungkan Mistral-7B-Instruct, FastAPI, SQLAlchemy, SQLite/SQL Server, embeddings MiniLM, dan FAISS; sinkronisasi database disebut setiap lima menit.
- **Data/akuisisi:** Skenario toko; penulis menyebut 52 percakapan dan 312 pasangan query–response dalam pembahasan. Pengujian berada dalam kondisi laboratorium, bukan validasi pelanggan produksi.
- **Preprocessing dan matching:** Analisis intent/entitas, pencarian semantik, pemeringkatan konteks, serta pengecekan fakta terhadap database. Mekanisme prioritas sumber dan bobot pemeringkatan belum cukup rinci untuk direplikasi hanya dari deskripsi umum tersebut.
- **Evaluasi/hasil:** Tabel 2 melaporkan faithfulness, relevance, context precision, dan context recall masing-masing 0,80; evaluasi manusia pada halaman 10 memberi skor sekitar 0,6–0,7 menurut dimensi.
- **Keterbatasan/kritik:** Skor seragam dengan SD 0,00 tetapi CI tidak nol memerlukan penjelasan. Rata-rata waktu 0,08 detik tidak mudah diselaraskan dengan distribusi log hingga 90 detik dan indikator waktu lain di paper. Rata-rata empat skor evaluasi diberi label overall accuracy, padahal bukan otomatis accuracy klasifikasi. Jangan jadikan angka ini target performa salon atau bukti peningkatan yang pasti.
- **Pemakaian:** Rujukan terdekat bahwa penggabungan database operasional dan RAG sudah ada. Celah yang mungkin diteliti adalah akurasi fakta dinamis, prioritas sumber, dan bukti lengkap pada pertanyaan campuran, yang masih harus diverifikasi dalam eksperimen sendiri.
- **Jejak bukti:** halaman PDF 5–10, 13, 15–17. **Status:** inti arsitektur; kepercayaan terhadap klaim numerik perlu kehati-hatian tinggi.

### P02 — Design of a RAG-Based Customer Service Chatbot Enhanced with Knowledge Graph and GPT Evaluation: A Case Study in the Import Trade Industry

- **Identitas:** Hsueh & Lin, 2026; Software; DOI `10.3390/software5020015`. [PDF][P02].
- **Masalah/metode:** Jawaban layanan pelanggan memerlukan penggabungan SOP, catatan rapat, keluhan, dan hubungan antar-entitas. Sistem menggabungkan retrieval vektor, QA terkurasi, Neo4j, dan penilaian GPT; jawaban berperingkat tinggi dapat disimpan dengan metadata.
- **Data/akuisisi:** 101 query dari enam kategori bisnis. Jawaban referensi diturunkan dari dokumen/resolusi perusahaan dan diperiksa pimpinan departemen; query diparafrasekan. QA retrieval dan query uji dijelaskan terpisah.
- **Preprocessing/matching:** Ekstraksi pengetahuan dokumen menjadi entitas–relasi, pencarian vektor dan graf, serta penyusunan konteks lintas sumber. Metadata memungkinkan penelusuran dan rollback.
- **Evaluasi/hasil:** LLM-only, RAG-only, dan RAG+KG memperoleh rata-rata skor GPT 28,65; 31,81; 34,58 dari maksimum 40. BLEU 0,0670; 0,2170; 0,2245 dan ROUGE-L 0,0356; 0,0406; 0,0501. RAG+KG menang pada 75/101 query.
- **Keterbatasan/kritik:** 26 query tidak dimenangkan sistem penuh; antara lain konflik bukti, aturan lama, dan preferensi judge. Perbandingan sistem penuh tidak mengisolasi kontribusi setiap komponen. BLEU/ROUGE mengukur overlap, bukan bukti kebenaran semantik penuh. Jawaban hasil model yang disimpan kembali memerlukan verifikasi agar kesalahan tidak berulang.
- **Pemakaian:** Acuan perbandingan fair, metadata, dan kasus informasi terbaru bertentangan dengan aturan lama. Penggunaan graf sendiri sudah ada; tidak perlu langsung membangun graf bila masalah salon dapat diuji dengan perutean sumber yang lebih sederhana.
- **Jejak bukti:** halaman 6–9, 13–16, 18–25. **Status:** inti metode integrasi dan analisis error.

### P03 — Lisa: a touristic chatbot for Lisbon

- **Identitas:** Cruz, Jardim & de Castro Neto, 2025; Information Technology & Tourism; DOI `10.1007/s40558-025-00339-x`. [PDF][P03].
- **Masalah/metode:** Informasi dan rekomendasi layanan wisata tersebar di website. Sistem memakai lebih dari 2.000 halaman web, Chroma, embeddings, BM25, serta hybrid search dengan Reciprocal Rank Fusion.
- **Data/akuisisi:** 251 QA tertutup dan 50 pertanyaan terbuka dibuat dengan bantuan model dan diperiksa manual. Evaluasi lanjutan dilakukan tiga pakar; eksperimen otomatis diulang 30 kali.
- **Preprocessing/matching:** Penghapusan boilerplate, struktur berulang, dan konten promosi yang tidak relevan; pengujian dataset sebelum/sesudah cleaning. Hasil dense dan BM25 digabung; jumlah dokumen konteks diuji.
- **Evaluasi/hasil:** Pada konfigurasi pembanding, SAS dense-cosine 52,97%, BM25 49,87%, hybrid-cosine 56,66%. Cleaning lanjutan menaikkan SAS dari 56,66% menjadi 65,73%. Model akhir GPT-4o mencapai SAS 71,36%; itu merupakan gabungan beberapa perubahan, bukan efek cleaning saja.
- **Keterbatasan/kritik:** Skor pertanyaan terbuka menilai apakah ada jawaban, bukan apakah jawaban pasti benar. Tidak diuji pada wisatawan nyata; pemisahan validation/test menjadi usulan perbaikan. Konfigurasi dua generator berbeda dalam jumlah konteks karena rate limit.
- **Pemakaian:** Rujukan kuat untuk dokumentasi web crawling dan preprocessing. Kepatuhan robots.txt pada proyek kita perlu dicatat sendiri; jangan mengasumsikan protokol akuisisi paper ini identik dengan proyek.
- **Jejak bukti:** halaman 1, 13–18, 20–21, 27. **Status:** inti akuisisi dan desain eksperimen.

### P04 — Design and Performance Evaluation of LLM-Based RAG Pipelines for Chatbot Services in International Student Admissions

- **Identitas:** Khasanova Zafar kizi & Suh, 2025; Electronics; DOI `10.3390/electronics14153095`. [PDF][P04].
- **Masalah/metode:** Informasi penerimaan tersebar dalam PDF dan FAQ. Membandingkan recursive/semantic chunking, dense, MMR, hybrid, MultiQuery/MultiVector, serta model komersial dan lokal.
- **Data/akuisisi:** Panduan PDF 29 halaman, 38 FAQ website, dan 11 FAQ tambahan. Evaluasi mencakup 62 QA manual dan 72 QA hasil LLM dengan 11 kelompok topik. Jangan menganggap kedua set mempunyai jumlah pertanyaan identik tanpa memeriksa berkas datanya.
- **Preprocessing/matching:** Label sumber PDF/FAQ, pemotongan teks, MiniLM 384 dimensi, FAISS; top-k 5. Retrieval dibandingkan pada korpus layanan yang sama.
- **Evaluasi/hasil:** Empat dimensi RAGAS, metrik NLP tambahan, SD/CI, dan latensi per tahap. OpenChat dengan recursive splitting dan hybrid retrieval dilaporkan unggul pada konfigurasi yang diuji, dengan konsekuensi latensi; tabel latensi beberapa konfigurasi mencapai sekitar 17,4 detik.
- **Keterbatasan/kritik:** Satu institusi, jumlah pertanyaan terbatas, jawaban manual oleh satu annotator. Hasil skor tinggi tidak membuktikan konfigurasi itu unggul untuk bahasa Indonesia atau perangkat kita. Instruksi untuk melakukan inferensi ketika konteks tidak langsung terkait perlu dihindari pada fakta harga yang harus pasti.
- **Pemakaian:** Template dokumentasi dataset, konfigurasi, dan analisis kualitas–latensi. Mendukung pelaporan keterbatasan anotator tunggal secara terbuka.
- **Jejak bukti:** halaman 3–6, 18–19. **Status:** inti desain eksperimen dan evaluasi.

### P05 — Implementation of Retrieval-Augmented Generation Method on Large Language Model for Development of Campus Service and Information Chatbot

- **Identitas:** Salman dkk., 2026; INOVTEK Polbeng – Seri Informatika; DOI `10.35314/3y9hy151`. [PDF][P05].
- **Masalah/metode:** Mengurangi informasi kampus tanpa dasar sumber. Menggunakan multilingual-e5-base, FAISS, BM25, RRF, cross-encoder multilingual, dan LLaMA 3.1 8B melalui Groq.
- **Data/akuisisi:** 29 dokumen teks dari website resmi USTI, delapan kategori; 13 query uji. Satu annotator menetapkan relevansi dokumen terhadap query.
- **Preprocessing/matching:** Normalisasi NFKC, tipografi dan whitespace; chunking, metadata sumber/indeks/rentang kata. Kandidat dense dan sparse digabung RRF; reranking memilih tiga chunk konteks akhir.
- **Evaluasi/hasil:** Tabel 6: hybrid P@3 71,7%, R@3 87,5%, F1@3 78,8%, NDCG@3 96,3%. Tabel 7: BERTScore-F1 LLM-only 84,8%, BM25 89,5%, dense 89,3%, hybrid 89,4%; faithfulness dense 93,6% dan hybrid 88,8%.
- **Keterbatasan/kritik:** Hybrid terbaik pada retrieval tidak sekaligus tertinggi pada faithfulness/BERTScore. Tabel 5 dan 6 berbeda sedikit angkanya; konfigurasi chunking juga mencantumkan target 150 kata di bawah minimum 180 kata. Hanya 13 query dan satu annotator membatasi generalisasi. Dokumen-level label dan klaim chunk-level perlu diselaraskan jika direplikasi.
- **Pemakaian:** Pembanding Indonesia dan bukti bahwa BM25+dense+RRF+reranking sudah dipublikasikan. F1 retrieval harus dibedakan dari BERTScore-F1 generasi.
- **Jejak bukti:** halaman 1, 4–10. **Status:** inti pembanding Indonesia; catatan konsistensi wajib dipertahankan.

### P06 — Design and Implementation of an Interactive Question-Answering System with Retrieval-Augmented Generation for Personalized Databases

- **Identitas:** Byun dkk., 2024; Applied Sciences; DOI `10.3390/app14177995`. [PDF][P06].
- **Masalah/metode:** Jawaban LLM perlu mengikuti dokumen personal yang dapat berubah. Menggunakan tagging, dokumen dalam SQL, ChromaDB, dan MongoDB untuk riwayat; lima LLM dan dua embedding dibandingkan.
- **Data/akuisisi:** Dataset commonsense AIHub berisi 100 item question–ground truth–context; paper juga membahas dataset artikel berita. Jangan menyamakan personalized database ini dengan tabel layanan/harga operasional hanya karena sama-sama memakai SQL.
- **Preprocessing/matching:** Dokumen ditag dan dikategorikan; konteks dicari berdasarkan kesamaan dan informasi tersimpan, lalu dipadukan dengan prompt serta riwayat percakapan.
- **Evaluasi/hasil:** Pada commonsense, ada-002 + GPT-3.5 memperoleh faithfulness 0,51 dan relevancy 0,86. Pada berita, relevancy konfigurasi ini 0,82, sedangkan context recall 0,51 dan kombinasi KR-SBERT + GPT-3.5 mencapai 0,68.
- **Keterbatasan/kritik:** Bergantung pada LLM dan cakupan database; transfer lintas domain belum terjamin. Narasi paper kadang menyebut faithfulness sebagai accuracy; dalam naskah kita definisinya harus tetap dibedakan.
- **Pemakaian:** Dasar pemisahan faithfulness, relevancy, context precision/recall serta trade-off kualitas, biaya, dan waktu. Bukan bukti bahwa model yang lebih besar selalu lebih baik.
- **Jejak bukti:** halaman 9–12, 16, 18–20. **Status:** inti manajemen dokumen dan evaluasi multidimensi.

### P07 — Evaluating LLM-Based Retrieval-Augmented Generation for Soil Science Question Answering

- **Identitas:** Topić, Bagić Babac & Mornar, 2026; Information; DOI `10.3390/info17090859`. [PDF][P07].
- **Masalah/metode:** Menentukan pilihan chunking, embedding, retrieval, dan generator untuk literatur ilmiah dengan kekhususan berbeda. Tiga tahap evaluasi membandingkan empat chunking, tiga embedding dalam evaluasi formal, lima retrieval, dan lima generator.
- **Data/akuisisi:** 326 QA pada korpus umum 140, domain-specific 101, geospatial 85. QA dibuat DeepSeek R1; 75 pasangan diperiksa satu reviewer. Provenance meliputi dokumen, halaman, dan chunk.
- **Preprocessing/matching:** PDF teks, beberapa strategi segmentasi, collection Chroma terpisah menurut embedding/korpus. Query menggunakan embedding yang sesuai collection. Dense, BM25, RRF, MMR, dan reranker dibandingkan.
- **Evaluasi/hasil:** Hybrid RRF recall@5 0,957; 0,960; 0,647 menurut korpus. BERTScore respons dilaporkan 0,909–0,927 dan faithfulness setidaknya 0,993. Reranker tidak selalu memperbaiki ranking.
- **Keterbatasan/kritik:** Ground truth retrieval pada tingkat **dokumen**: mengambil chunk mana pun dari dokumen sumber dapat dihitung berhasil meskipun bukan bukti jawaban. Faithfulness berbasis NLI yang tinggi tidak menjamin kelengkapan/kebenaran jawaban. Tidak ada penilaian manusia atas seluruh keluaran RAG; QA sintetis berpotensi lebih mudah daripada query pengguna mandiri.
- **Pemakaian:** Acuan metadata dan desain komponen. Untuk salon, label bukti sebaiknya menunjuk passage/record yang benar-benar mendukung jawaban, bukan hanya file asal.
- **Jejak bukti:** halaman 6–7, 10–15, 26, 37–39. **Status:** inti metodologi korpus dan audit evaluasi.

### P08 — Efficacy Evaluation and Optimization of RAG Knowledge Bases in the Oil and Gas Industry Using an LLM-as-a-Judge Mechanism

- **Identitas:** Yang dkk., 2026; Energies; DOI `10.3390/en19174207`. [PDF][P08].
- **Masalah/metode:** Retrieval gagal, ketidaksesuaian angka/entitas, pengetahuan kedaluwarsa, dan generasi tanpa bukti. DAAE mengatur evaluasi Data, Retrieval, Generation, Utility dan menghubungkannya dengan tindakan perbaikan.
- **Data/akuisisi:** Benchmark 150 pertanyaan bisnis beranotasi ahli pada satu knowledge base industri. Tambahan ablation bertahap 50 pertanyaan dan validasi judge–manusia pada 50 respons.
- **Preprocessing/matching:** Pembersihan, semantic-aware chunking, metadata, hybrid BM25+dense, reranker, prompt dengan sitasi/refusal. Kegagalan retrieval tetap masuk statistik end-to-end.
- **Evaluasi/hasil:** Hit@5 87/150 menjadi 134/150; context precision 0,64 menjadi 0,88; faithfulness 0,65 menjadi 0,94. Validasi terbatas melaporkan Pearson r 0,82 untuk faithfulness dan kappa 0,79 untuk correctness.
- **Keterbatasan/kritik:** Before–after sistem penuh tidak menetapkan efek kausal tiap komponen. Baseline awal relatif lemah; tidak ada locked held-out split atau repeated-run lengkap. Sebagian log individual/parameter historis tidak tersedia, sehingga tidak semua CI/signifikansi bisa direkonstruksi.
- **Pemakaian:** Acuan kuat untuk menyimpan log per pertanyaan, memisahkan kegagalan teknis dari skor nol yang sah, menguji angka dan kemutakhiran, serta melaporkan ketidakpastian.
- **Jejak bukti:** halaman 1, 9–10, 14–17. **Status:** inti desain evaluasi dan diagnosis error.

### P09 — Evaluating Retrieval Augmented Generation: A Comprehensive Review of Evaluation Dimensions, Question Types, and Application

- **Identitas:** Knollmeyer dkk., 2026; SN Computer Science; DOI `10.1007/s42979-026-05134-x`. [PDF][P09].
- **Masalah/metode:** Tidak seragamnya evaluasi RAG dan hubungan metrik dengan data serta tahapan pipeline. SLR menyintesis 12 studi dengan matriks konsep.
- **Data/akuisisi:** Literatur penelitian evaluasi; bukan dataset pelanggan atau korpus perawatan. Hasilnya berupa kerangka pemilihan evaluasi.
- **Matching/evaluasi:** Memetakan context relevance, faithfulness, answer relevance, correctness, dan citation quality terhadap evaluator, dataset, single-hop/multi-hop, serta fase pipeline.
- **Hasil:** Kerangka dan rekomendasi implementasi evaluasi; tidak menguji bahwa satu metode retrieval baru menaikkan skor tertentu pada salon.
- **Keterbatasan/kritik:** Sintesis dibatasi studi yang diseleksi dan perkembangan bidang; rekomendasi konseptual perlu dioperasionalkan serta divalidasi pada dataset sendiri.
- **Pemakaian:** Menentukan kebutuhan anotasi untuk setiap metrik, memisahkan jenis pertanyaan, serta mencatat parameter chunking, retrieval, generator, prompt, dan judge.
- **Jejak bukti:** halaman 1, 4–10, 12–13. **Status:** inti dasar pemilihan parameter uji.

### P10 — RAGAS: Automated Evaluation of Retrieval Augmented Generation

- **Identitas:** Es, James, Espinosa-Anke & Schockaert, 2024; EACL System Demonstrations, prosiding terbit. [PDF][P10].
- **Masalah/metode:** Evaluasi RAG membutuhkan beberapa dimensi dan pengurangan beban anotasi. Faithfulness dinilai melalui pemecahan klaim dan pengecekan dukungan konteks; relevancy melalui pertanyaan yang direkonstruksi dan embedding; context relevance melalui kalimat konteks yang relevan.
- **Data/akuisisi:** WikiEval dari 50 halaman Wikipedia, dengan perbandingan jawaban/konteks yang dianotasi dua orang.
- **Evaluasi/hasil:** Tabel 4 melaporkan agreement pairwise terhadap manusia: faithfulness 0,95, answer relevance 0,78, context relevance 0,70. Ini **agreement evaluator**, bukan skor mutu chatbot RAG salon.
- **Keterbatasan/kritik:** Ketergantungan model judge, prompt, variasi antar-run, dan kesulitan memilih kalimat konteks. Paper ini terutama mendefinisikan tiga dimensi tersebut; jangan menyatakan seluruh variasi context precision/recall di library modern identik dengan formulasi dalam paper ini.
- **Pemakaian:** Referensi primer evaluasi. Rubrik buatan sendiri bernama RAGAS tidak otomatis merupakan implementasi RAGAS. Versi, fungsi metrik, input, dan model evaluator harus dicatat.
- **Jejak bukti:** halaman 3–7. **Status:** inti evaluasi; prosiding dibedakan dari jurnal.

### P11 — Enabling Large Language Models to Generate Text with Citations

- **Identitas:** Gao, Yen, Yu & Chen, 2023; EMNLP, prosiding terbit. [PDF][P11].
- **Masalah/metode:** Jawaban yang lancar belum tentu benar atau didukung sitasi. ALCE mengevaluasi generasi dengan bukti, fluency, correctness, dan citation quality melalui retrieval, prompting, dan NLI.
- **Data/akuisisi:** ASQA, QAMPARI, ELI5; dipilih 1.000 contoh development dari setiap dataset. Korpus Wikipedia dan Sphere digunakan sesuai dataset.
- **Matching/evaluasi:** Pernyataan jawaban dipasangkan dengan passage yang dikutip. Citation recall menilai apakah pernyataan didukung gabungan sitasinya; citation precision menilai sitasi yang tidak relevan. Correctness diukur berbeda menurut jenis jawaban, termasuk exact-match recall/list matching/claim recall.
- **Hasil:** Sekitar 50% generasi baseline ChatGPT/GPT-4 pada ELI5 belum didukung sitasi secara lengkap. Menambah passage tidak konsisten membantu semua model.
- **Keterbatasan/kritik:** Kualitas NLI, dukungan parsial, dan keterbukaan jawaban memengaruhi skor. Benchmark bukan khusus bahasa Indonesia atau fakta operasional dinamis.
- **Pemakaian:** Dasar memeriksa tautan sumber yang benar-benar mendukung klaim. Untuk layanan/harga, provenance record database harus dibedakan dari sitasi artikel perawatan.
- **Jejak bukti:** halaman 1–4, 10. **Status:** inti evaluasi dukungan sitasi.

### P12 — TechDocRAG: Relation-Preserving Retrieval-Augmented Generation for Technical Documents

- **Identitas:** Lee & Choi, 2026; AI; DOI `10.3390/ai7050161`. [PDF][P12].
- **Masalah/metode:** Flattening dokumen memutus hubungan klausa, tabel, gambar, dan prosedur. Sistem membangun graf elemen heterogen dan tiga tampilan retrieval: identifier, summary, raw evidence.
- **Data/akuisisi:** Subset terkurasi lebih dari 7.500 QA dari MPMQA, DesignQA, MMLongBench-Doc, LongDocURL. Ukuran benchmark penuh di tabel bukan jumlah contoh yang semuanya diuji.
- **Preprocessing/matching:** Parsing/OCR, normalisasi identifier, ekstraksi relasi, BM25 identifier, embedding summary, graph expansion, raw evidence bundling, dan budget konteks yang dikontrol.
- **Evaluasi/hasil:** Penulis melaporkan rata-rata peningkatan 20,3 poin terhadap baseline flat terkuat dan strict raw evidence hit rate 0,510 menjadi 0,942 pada subset beranotasi. Metrik meliputi Recall@k, MRR, evidence connectivity, claim support, dan konsistensi versi.
- **Keterbatasan/kritik:** Bergantung pada parsing dan identifier; anotasi bukti/relasi mahal. Tingkat matching, subset, dan denominator hasil berbeda harus dipertahankan saat mengutip. Kelebihan pada manual teknik tidak otomatis berlaku pada FAQ pendek salon.
- **Pemakaian:** Mempertahankan pasangan nama layanan–harga–syarat dan metadata dokumen. Kerangka lengkap tidak perlu direplikasi bila kebutuhan hanya fakta tabel sederhana.
- **Jejak bukti:** halaman 1, 8–14. **Status:** pendalaman relasi dan provenance.

### P13 — SES-RAG: An Adaptive Framework with ModernBERT Segmentation and Generative-Alignment Expansion

- **Identitas:** Gao, He & Zhang, 2026; Applied Sciences; DOI `10.3390/app16104849`. [PDF][P13].
- **Masalah/metode:** Pemotongan jendela tetap, ketidakselarasan query–dokumen, dan top-k statis. Tiga komponen: semantic segmenter ModernBERT, GAQE dengan hypothetical document dan residual fusion, serta Information Density Truncation.
- **Data/akuisisi:** NarrativeQA, QuALITY, QASPER; eksperimen segmentasi tambahan pada sepuluh dokumen WikiText. Generator pembanding dibuat sama, GPT-4o-mini; lingkungan melibatkan GPU 24 GB.
- **Preprocessing/matching:** Batas chunk berbasis pasangan kalimat; expansion menjaga embedding query asli; context cutoff dipilih berdasarkan skor relevansi kumulatif dengan penalti panjang.
- **Evaluasi/hasil:** QASPER F1-Match naive 37,23 dan SES-RAG 41,06; QuALITY accuracy 70,67 menjadi 74,33. NarrativeQA menggunakan ROUGE/BLEU/METEOR, bukan F1 retrieval.
- **Keterbatasan/kritik:** Memerlukan training segmenter dan panggilan expansion; sebutan lightweight harus dikaitkan dengan perangkat serta baseline yang digunakan. Penjelasan ablation perlu dicocokkan dengan tabel karena penambahan modul tunggal dan penghilangan modul tidak identik.
- **Pemakaian:** Kandidat pengujian pemilihan konteks adaptif bila pilot menunjukkan konteks terlalu panjang/bising. Bukan pilihan otomatis dengan batas anggaran proyek.
- **Jejak bukti:** halaman 1, 7–15. **Status:** pendalaman chunking/seleksi konteks.

### P14 — Retrieval-Augmented Generation (RAG) Chatbot for Handling Customer Complaints in the Energy Sector

- **Identitas:** Putro dkk., 2025; Jurnal Infomedia. [PDF][P14].
- **Masalah/metode:** Pemanfaatan catatan keluhan internal untuk jawaban berbahasa Indonesia. Memakai normalisasi bahasa, segmentasi waktu, anonimisasi, narasi, FAISS, LLM lokal melalui Ollama/LangChain, serta klarifikasi dan fallback.
- **Data/akuisisi:** Keluhan dari database internal PLN. Evaluasi yang disajikan berpusat pada lima query representatif dan lima reviewer; jangan mengasumsikan benchmark besar dari skala perusahaan.
- **Preprocessing/matching:** Record terstruktur diubah menjadi narasi, di-embedding, lalu dicari top-k. Ini berbeda dari mengambil harga/status langsung melalui query database saat pengguna bertanya.
- **Evaluasi/hasil:** BLEU-4 46,5, ROUGE-L 0,63, helpfulness 92%; pembanding LLM-only dan retrieval-only juga dilaporkan.
- **Keterbatasan/kritik:** Lima query terlalu kecil untuk klaim generalisasi. Definisi/denominator beberapa indikator dan kesesuaian referensi jawaban pendek terhadap keluaran panjang perlu audit; formula BLEU/ROUGE yang disederhanakan jangan disalin sebagai definisi standar. Model MiniLM yang disebut multilingual perlu dibedakan dari model multilingual khusus.
- **Pemakaian:** Contoh dokumentasi data internal dan mekanisme klarifikasi. Tidak cukup sebagai satu-satunya justifikasi metode atau target skor.
- **Jejak bukti:** halaman 2–6. **Status:** pembanding aplikasi Indonesia dengan bukti terbatas.

### P15 — Dual index retrieval augmented generation for pedagogically aligned mathematics problem solving support in mathematics education

- **Identitas:** Jiang, Deng & Wang, 2026; Discover Computing; DOI `10.1007/s10791-026-10432-2`. [PDF][P15].
- **Masalah/metode:** Retrieval menemukan topik mirip tetapi struktur solusi salah. ChromaDB dipadukan dengan knowledge graph NetworkX dan filtering pascaretrieval.
- **Data/akuisisi:** Korpus 2.548 node matematika; validasi retrieval memakai 424 dokumen tingkat pertanyaan dari 29 Markdown dan 50 query: 25 exact, 25 fuzzy. Pemeriksaan judge–manusia pada 30 kasus.
- **Matching/evaluasi:** Vector-only, hybrid, reranking, dan full filtering dibandingkan dengan Precision@10, Recall@10, bootstrap CI, serta paired tests. Generasi memakai faithfulness/logical consistency/pedagogical alignment.
- **Hasil:** Recall@10 vector-only 0,058 dan hybrid/full 0,181; Precision@10 0,028 menjadi 0,074. Filtering tidak menambah hasil agregat dibanding hybrid pada setting yang dilaporkan.
- **Keterbatasan/kritik:** Sampel kecil dan domain matematika Tionghoa. Beberapa rumus muncul sebagai placeholder dalam ekstraksi teks; angka yang dipakai di sini dibatasi tabel dan narasi yang terbaca, bukan merekonstruksi simbol yang hilang. Hasil generasi agregat bersifat pendahuluan.
- **Pemakaian:** Contoh bahwa komponen tambahan boleh tidak bermanfaat. Hard-negative test salon dapat memisahkan layanan yang namanya mirip tetapi harga/syaratnya berbeda.
- **Jejak bukti:** halaman 7–11. **Status:** pembanding tambahan dan pelaporan hasil negatif.

### P16 — Retrieval-Augmented Generation (RAG)

- **Identitas:** Klesel & Wittmann, 2025; Business & Information Systems Engineering, artikel Catchword; DOI `10.1007/s12599-025-00945-3`. [PDF][P16].
- **Masalah/metode:** Pengetahuan organisasi tidak selalu tersedia dalam parameter LLM. Artikel menjelaskan memori parametrik/nonparametrik, retriever, embeddings, augmentation, peluang dan tantangan.
- **Data/evaluasi/hasil:** Artikel konseptual dengan ilustrasi dan sintesis literatur; bukan eksperimen chatbot salon dan tidak memberikan skor yang dapat dipakai sebagai baseline lokal.
- **Matching:** Menekankan embedding query dan dokumen harus sesuai; membahas pemanfaatan sumber eksternal dan grounding.
- **Keterbatasan:** Konsep umum tidak menetapkan konfigurasi terbaik atau membuktikan solusi otomatis bebas halusinasi.
- **Pemakaian:** Landasan teori terbit 2025, terutama ketika batas referensi 2021–2026 tidak memasukkan paper fondasi 2020. Klaim empiris tetap harus ditelusuri ke studi primer.
- **Jejak bukti:** halaman 1–8. **Status:** landasan konseptual.

### P17 — Retrieval-augmented generation for natural language processing: a survey

- **Identitas:** Wu dkk., 2026; Artificial Intelligence Review; DOI `10.1007/s10462-026-11605-7`. [PDF][P17].
- **Masalah/metode:** Banyak desain retriever dan fusion untuk mengatasi keterbatasan pengetahuan LLM. Survei menyusun taksonomi query-based, logits-based, latent, dan parametric fusion serta pembahasan pembaruan knowledge base.
- **Data/evaluasi/hasil:** Literatur berbagai tugas NLP; hasil berupa pemetaan arsitektur, benchmark, efisiensi, dan tantangan, bukan satu eksperimen baru di salon.
- **Matching:** Berguna membedakan fusion pada hasil pencarian dari fusion di bagian internal generator; keduanya bukan istilah yang dapat dipertukarkan.
- **Keterbatasan:** Mencakup studi dengan status publikasi dan protokol beragam; keberadaan suatu metode dalam survei tidak otomatis memastikan semua sumber primernya memenuhi seleksi kita.
- **Pemakaian:** Peta pencarian studi primer untuk menguji calon kebaruan. Jangan menjadikan pernyataan umum survei sebagai bukti bahwa masalah tertentu terjadi di TIEN Salon.
- **Jejak bukti:** halaman 1–3 dan pembahasan arah riset graf pada halaman 41. **Status:** penunjang teori dan penelusuran lanjutan.

### P18 — A Survey of conversational AI from rule based to generative and retrieval augmented generation chatbots

- **Identitas:** Ghaywat dkk., 2026; Discover Artificial Intelligence; DOI `10.1007/s44163-026-02373-y`. [PDF][P18].
- **Masalah/metode:** Keandalan chatbot dipengaruhi interaksi chunking, embedding, retrieval, reranking, grounding, attribution, dan evaluasi. Survei memakai protokol seleksi dan analisis desain sistem.
- **Data/akuisisi:** Literatur dari ACL, IEEE, ACM, arXiv, dan penelusuran silang; mencakup preprint serta publikasi terbit. Status artikel survei ini dan status semua paper yang dirujuknya harus dibedakan.
- **Evaluasi/hasil:** Sintesis failure modes dan trade-off sistem; tidak menghasilkan skor benchmark salon atau bukti keunggulan tunggal satu algoritma.
- **Keterbatasan:** Cakupan luas; hubungan mekanisme dengan hasil studi tertentu perlu ditelusuri kembali ke eksperimen primer.
- **Pemakaian:** Pemeriksaan kelengkapan rancangan dan kategori error. Lebih rendah prioritas daripada studi komparatif yang dekat dengan kebutuhan database/dokumen.
- **Jejak bukti:** halaman 1–4 dan pembahasan tantangan akhir. **Status:** survei penunjang.

### P19 — A survey on retrieval-augmentation generation (RAG) models for healthcare applications

- **Identitas:** Abo El-Enen, Saad & Nazmy, 2025; Neural Computing and Applications; DOI `10.1007/s00521-025-11666-9`. [PDF][P19].
- **Masalah/metode:** Akurasi, kemutakhiran, istilah khusus, dan bukti dalam aplikasi kesehatan. Survei membahas Naive, Advanced, Modular RAG, dataset, evaluasi, dan deployment.
- **Data/preprocessing/matching:** Literatur dan benchmark kesehatan; membahas metadata, provenance, chunking, query enhancement, dan retrieval khusus domain. Korpus ini bukan korpus pengetahuan salon siap pakai.
- **Evaluasi/hasil:** Sintesis berbagai penelitian dan metrik. Angka antarstudi tidak menjadi hasil eksperimen baru artikel survei ini dan tidak setara langsung karena dataset/protokol berbeda.
- **Keterbatasan:** Domain klinis lebih luas dan berbeda dari konsultasi salon. Survei bukan panduan diagnosis/terapi; klaim perawatan spesifik harus ditelusuri ke sumber klinis yang tepat.
- **Pemakaian:** Mendukung pemilihan sumber perawatan yang dapat dilacak dan pembatasan jawaban. Tidak dipakai untuk menyatakan chatbot salon terbukti aman secara medis.
- **Jejak bukti:** halaman 1–3, 9, 25–28, 72. **Status:** pendukung tata kelola sumber perawatan.

### P20 — Pengaruh kualitas layanan, kualitas produk dan harga terhadap kepuasan pelanggan salon di Tanjung Tabalong Kalimantan Selatan

- **Identitas:** Rachmawati dkk., 2025; Jurnal Akuntansi, Ekonomi dan Manajemen Bisnis; DOI `10.55606/jaemb.v5i3.7103`. [PDF][P20].
- **Masalah/metode:** Hubungan kualitas layanan, kualitas produk, dan harga dengan kepuasan pelanggan Salon RCP. Pendekatan kuantitatif, kuesioner Likert dan regresi linier berganda.
- **Data/akuisisi:** 100 pelanggan salon. Abstrak menyebut purposive sampling; uraian ukuran sampel perlu dibaca konsisten dengan metode utama sebelum direplikasi.
- **Matching/evaluasi/hasil:** Tidak mempunyai retrieval atau generasi. Instrumen diuji dan hubungan ketiga variabel dengan kepuasan dilaporkan signifikan.
- **Keterbatasan:** Satu salon dan desain observasional; tidak membuktikan kesalahan informasi harga di TIEN atau dampak kausal chatbot pada kepuasan.
- **Pemakaian:** Mendukung alasan memilih informasi layanan/harga sebagai objek penting. Bukti masalah operasional TIEN tetap membutuhkan observasi, wawancara, atau pertanyaan pelanggan lokal.
- **Jejak bukti:** halaman 1, 5, 9. **Status:** prioritas konteks objek, bukan pembanding algoritma.

### P21 — Perancangan bangun sistem informasi jasa kecantikan berbasis web pada Annisavy

- **Identitas:** Dea Amelia Putri, Hari Murti & Sulastri, 2026; INTECOMS. DOI dari daftar bibliografi awal pengguna: `10.31539/77h0tp19`; tidak digunakan sebagai bukti hasil karena tidak terbaca pada kutipan bagian PDF yang diperiksa. [PDF][P21].
- **Masalah/metode:** Pemesanan dan pencatatan layanan/transaksi manual. Sistem web dikembangkan melalui Waterfall, wawancara, observasi, dan pengujian black-box.
- **Data/akuisisi:** Alur kerja Annisavy dan kebutuhan customer/admin/pemilik/petugas; layanan termasuk nail art, eyelash, MUA. Bukan khusus perawatan rambut.
- **Matching/evaluasi/hasil:** Tidak ada algoritma RAG. Fungsi booking, jadwal, layanan, transaksi, dan laporan diuji. Tabel halaman 7 memuat pengujian awal dengan masalah laporan mingguan/bulanan dan pengujian akhir dengan hasil sesuai.
- **Keterbatasan:** Lulus black-box menunjukkan fungsi yang diuji berjalan, bukan bukti peningkatan akurasi jawaban, kepuasan, atau efisiensi kausal.
- **Pemakaian:** Penelitian terkait tingkat aplikasi. Ketiadaan RAG dalam paper ini tidak membuktikan belum ada RAG salon secara global.
- **Jejak bukti:** halaman 1, 3, 7–8. **Status:** prioritas konteks aplikasi.

### P22 — Profil pengetahuan, ketepatan tindakan, dan pemilihan produk dalam mengatasi ketombe pada mahasiswi berhijab di Universitas Airlangga

- **Identitas:** Prayogo dkk., 2024; Jurnal Farmasi Komunitas. DOI dari bibliografi awal pengguna: `10.20473/jfk.v11i1.52621`. [PDF][P22].
- **Masalah/metode:** Pengetahuan, tindakan, dan pilihan produk belum selalu konsisten. Survei deskriptif purposive dengan kuesioner, bukan eksperimen intervensi chatbot.
- **Data/akuisisi:** 161 mahasiswi baru berhijab; 139 pernah berketombe. Pengumpulan kuesioner 27 September–3 Oktober 2023; tahun publikasi tetap 2024.
- **Evaluasi/hasil:** Pada 139 responden, Tabel 2 mencatat tindakan tepat 63, kurang tepat 74, tidak tepat 2. Denominator ini berbeda dari seluruh 161 responden. Penulis menyimpulkan edukasi masih diperlukan.
- **Keterbatasan/kritik:** Tabel 2 salah memberi judul kolom seolah pemilihan sampo, padahal isi/pembahasan tindakan. Narasi beberapa jumlah juga tidak sepenuhnya konsisten. Jangan mengutip angka prevalensi nasional dari pendahuluan tanpa sumber primer atau menggeneralisasi populasi ini menjadi pelanggan TIEN.
- **Pemakaian:** Mendukung kebutuhan informasi perawatan pada populasi yang diteliti. Jawaban terapi dan ground truth perawatan tidak boleh otomatis diambil dari seluruh pernyataan artikel survei ini.
- **Jejak bukti:** halaman 1, 3, 5–6. **Status:** prioritas konteks edukasi, sumber pengetahuan bersyarat.

### P23 — 3D Hair Style Recommendation and Salon Scheduling

- **Identitas:** Mali dkk., 2025; IEEE ICETI4T, prosiding terbit; DOI `10.1109/ICETI4T63625.2025.11132264`. [PDF][P23].
- **Masalah/metode:** Menggabungkan pencarian salon, reservasi, dan visualisasi/rekomendasi gaya rambut. Deskripsi sistem mencakup penjadwalan, notifikasi, pencocokan gaya, dan visualisasi 3D.
- **Data/akuisisi:** Implementasi aplikasi dan data layanan/jadwal. Rincian benchmark yang memadai untuk mereplikasi seluruh klaim pengalaman pengguna tidak dijadikan dasar angka dalam mapping ini.
- **Matching/evaluasi/hasil:** Pencocokan gaya dan penjadwalan, bukan retrieval teks untuk RAG. Bagian hasil membahas fungsi sistem, UI, dan kinerja aplikasi.
- **Keterbatasan:** Klaim efektivitas/personalization tidak otomatis membuktikan peningkatan terukur pada pelanggan tanpa protokol dan denominator jelas. Pembahasan CV hanya dicatat sebagai ruang lingkup paper; tidak menjadi arah eksperimen RAG kita.
- **Pemakaian:** Pembanding fitur aplikasi salon; opsional untuk pekerjaan terkait jika ruang naskah memungkinkan.
- **Jejak bukti:** halaman 1, 3–5. **Status:** konteks aplikasi opsional; prosiding dibedakan dari jurnal.

### P24 — Factors related to the incidence of pityriasis capitis in students of the Faculty of Medicine, Muslim University of Indonesia, class 2021

- **Identitas:** Agriani dkk., 2026; Syifa’ Medika. DOI dari bibliografi awal pengguna: `10.32502/sm.v16i2.10301`. [PDF][P24].
- **Masalah/metode:** Faktor pemakaian jilbab dan perawatan terkait ketombe pada populasi mahasiswi. Penelitian cross-sectional memakai kuesioner dan Chi-square.
- **Data/akuisisi:** 199 mahasiswi Fakultas Kedokteran UMI. Angkatan 2021 pada judul bukan tahun publikasi.
- **Evaluasi/hasil:** Penulis melaporkan hubungan durasi pemakaian, bahan/warna jilbab, dan kebiasaan perawatan dengan kejadian ketombe; abstrak menyebut p < 0,001 untuk faktor yang diringkas.
- **Keterbatasan:** Hubungan observasional bukan kausalitas; self-report dan populasi khusus membatasi generalisasi. Tidak menilai RAG atau menguji terapi.
- **Pemakaian:** Pendukung konteks bersyarat apabila ketombe termasuk pertanyaan chatbot. Hindari klaim sebab-akibat dan rekomendasi pengobatan yang melampaui data.
- **Jejak bukti:** halaman 1, 10. **Status:** opsional perawatan kulit kepala.

### P25 — An analysis of strategic planning of the development of beauty industry in Indonesia

- **Identitas:** Horas dkk., 2026; International Journal of Economics, Business and Accounting Research; DOI dari bibliografi awal pengguna `10.29040/ijebar.v10ispecialissue.19257`. [PDF][P25].
- **Masalah/metode:** Faktor internal/eksternal pengembangan industri kecantikan Indonesia. Kajian kualitatif berbasis data sekunder memakai Porter Diamond, SWOT, dan TOWS.
- **Data/evaluasi/hasil:** Literatur/data industri; menghasilkan pemetaan strategi, termasuk inovasi, kapasitas riset, bahan baku, kolaborasi, dan kebijakan. Tidak mempunyai benchmark retrieval atau pelanggan TIEN.
- **Matching:** TOWS merupakan pemetaan strategi bisnis, berbeda dari matching query–dokumen dalam RAG.
- **Keterbatasan:** Cakupan industri sangat luas; tidak membuktikan masalah konsultasi salon atau kinerja suatu metode AI. Angka pertumbuhan industri perlu ditelusuri kembali ke sumber primer.
- **Pemakaian:** Pelengkap latar objek jika diperlukan; tidak perlu membuka pendahuluan dengan narasi pertumbuhan teknologi/industri yang panjang.
- **Jejak bukti:** halaman 1, 13. **Status:** pelengkap dengan relevansi langsung terendah.

## 5. Sintesis: apa yang sudah ada dan apa yang belum boleh diklaim

1. **Database operasional + RAG sudah ada** pada P01; personalisasi dokumen dengan SQL juga sudah dibahas P06. Integrasi dua teknologi ini bukan kebaruan otomatis.
2. **BM25 + dense + RRF/reranking sudah ada**, termasuk pada paper Indonesia P05. Mengganti objek kampus menjadi salon belum menunjukkan kontribusi metode.
3. **Relasi lintas sumber/graf, provenance, dan bukti terhubung sudah diteliti** pada P02/P12/P15. Penambahan graf juga bukan jaminan hasil lebih baik.
4. **Metrik yang berbeda dapat bergerak berbeda arah.** P05 menunjukkan retrieval hybrid lebih baik pada metrik tertentu, tetapi faithfulness lebih rendah dari dense. P03/P04 juga memperlihatkan trade-off kualitas–waktu. Ini bukan kontradiksi matematis: objek yang diukur berbeda.
5. **Kelengkapan bukti dan kebenaran fakta tidak identik dengan kemiripan teks.** P07/P09/P10/P11 membantu membedakan jawaban relevan, setia pada konteks, benar terhadap referensi, dan memiliki sitasi pendukung.
6. **Bukti konteks salon belum membuktikan masalah lokal.** P20/P21/P22 mendukung objek dan kebutuhan informasi terbatas. Masalah nyata TIEN perlu dibuktikan melalui data/observasi sendiri.

### Calon masalah penelitian paling sesuai untuk diuji

**Ketidaklengkapan dan ketidaktepatan jawaban pertanyaan campuran ketika fakta operasional salon yang berubah harus digabung dengan pengetahuan perawatan dari dokumen.** Contoh: “Perawatan untuk rambut kering yang tersedia apa, berapa harganya sekarang, dan apa dasar saran perawatannya?”

Dalam contoh tersebut, harga/ketersediaan harus mengikuti database yang berlaku, sedangkan penjelasan perawatan harus mempunyai sumber dokumen yang layak. Pertanyaan “mana sumber yang berwenang untuk klaim ini?” berbeda dari “passage mana paling mirip secara semantik?”.

Ini adalah **hipotesis arah penelitian hasil sintesis**, bukan klaim bahwa belum ada orang yang menelitinya. P01/P02/P08 bahkan memperlihatkan topik yang berdekatan. Sebelum menyatakan novelty, lakukan pencarian terarah tentang source routing, heterogeneous/structured–unstructured retrieval, source authority, temporal consistency, dan mixed-query evidence coverage, lalu bandingkan desain secara rinci.

### Tiga calon fokus, pilih satu setelah pilot

| Calon fokus | Kapan layak dipilih | Kontribusi yang perlu dibuktikan | Rujukan awal |
|---|---|---|---|
| Perutean dan prioritas sumber berbasis jenis fakta | Pilot menunjukkan harga/layanan salah atau tertukar dengan dokumen lama | Sumber operasional yang benar dipilih tanpa kehilangan penjelasan dokumenter | P01, P02, P06, P08 |
| Seleksi konteks dengan cakupan bukti pertanyaan campuran | Pilot menunjukkan salah satu subpertanyaan tidak terjawab | Bukti untuk seluruh kebutuhan pertanyaan ditemukan dengan budget konteks yang sebanding | P03, P05, P07, P12, P13 |
| Verifikasi klaim dan abstention saat bukti kurang/bertentangan | Pilot menunjukkan jawaban tetap diberikan meskipun sumber tidak mendukung | Dukungan klaim/kebenaran meningkat dengan penolakan yang terukur dan coverage tetap dilaporkan | P08, P09, P10, P11, P14 |

Metode spesifik dan judul final belum ditetapkan. Jangan menggabungkan semua kandidat hanya untuk terlihat kompleks. Hasil negatif tetap perlu dicatat jika intervensi tidak mengungguli baseline.

## 6. Akuisisi, preprocessing, dan matching untuk proyek

### Bedakan tiga jenis bahan

| Bahan | Fungsi | Contoh | Aturan |
|---|---|---|---|
| Literatur metode/evaluasi | Menjelaskan pilihan eksperimen dan menulis paper | P01–P19 | Tidak otomatis dimasukkan sebagai pengetahuan jawaban pelanggan |
| Data operasional salon | Sumber layanan, harga, durasi, ketersediaan/syarat yang benar | Tabel layanan dari database TIEN | Simpan ID record, field, waktu snapshot, dan versi; fakta bisnis mengikuti sumber berwenang ini |
| Dokumen pengetahuan perawatan | Dasar jawaban edukasi/perawatan | Sumber primer/pedoman/web tepercaya yang diseleksi; P22/P24 hanya bersyarat | Telaah isi dan batas klaim; status terbit saja tidak menjamin semua isi sesuai untuk ground truth |

### Rancangan pencatatan akuisisi

- Database: ekspor snapshot untuk eksperimen dengan `service_id`, nama, harga, satuan, durasi, syarat, `updated_at`. Catat field yang kosong; jangan mengarang nilai.
- PDF: simpan judul, penulis, tahun, DOI/URL, hash, hak akses, halaman, bagian, teks asli, dan bukti yang mendukung tiap calon jawaban.
- Web: pilih sumber sesuai topik; periksa robots.txt sebelum crawl, patuhi aturan akses, catat URL, tanggal akses, tanggal publikasi/pembaruan jika tersedia, cakupan halaman, dan status pengambilan. Jangan mengklaim paper terdahulu telah menjalankan prosedur yang sama tanpa bukti.
- Query pengguna: kumpulkan pertanyaan nyata jika tersedia, hilangkan identitas pribadi; jika disusun peneliti, beri label asalnya dan jangan menyebutnya data pelanggan nyata.

### Preprocessing yang perlu didokumentasikan

1. Validasi file, deduplikasi hash/isi, identifikasi dokumen scan dan halaman ekstraksi gagal.
2. Ekstraksi teks sambil mempertahankan judul bagian, tabel, satuan, negasi, dan pasangan layanan–harga. Hapus boilerplate berulang; hindari cleaning yang mengubah angka atau makna.
3. Normalisasi Unicode/whitespace secara konservatif. PDF rumus/tabel yang rusak ditandai untuk pemeriksaan visual; jangan mengisi simbol yang tidak terbaca dengan tebakan.
4. Segmentasi dengan parameter tercatat. Uji baseline chunking terlebih dahulu; jangan menganggap semantic chunking pasti unggul untuk semua dokumen.
5. Metadata minimal: `document_id`, `source_type`, URL/DOI, halaman/bagian, `chunk_id`, rentang bukti, tanggal/versi, hash. Record database tetap dapat dikenali sebagai record, bukan sekadar paragraf tanpa asal.
6. Gunakan embedding yang sama untuk query dan collection dokumen. Fallback embedding yang berbeda tidak boleh dicampur diam-diam dalam index yang sama.

### Proses matching yang perlu dijelaskan di metode

**Query → kebutuhan informasi/subpertanyaan → pemilihan sumber → retrieval record/passage → penggabungan bukti → generasi → pemeriksaan klaim/sitasi.**

Untuk setiap query uji, buat gold evidence berupa ID record/field atau passage yang mendukung jawaban. Query murni harga berbeda jalur kebutuhannya dari query edukasi; query campuran memerlukan keduanya. Jika dua sumber berisi harga berbeda, kebenaran ditentukan snapshot database yang berlaku, bukan jumlah dokumen atau skor cosine tertinggi.

Perutean berbasis aturan yang jelas dapat menjadi baseline. Query decomposition atau perutean dengan model merupakan kandidat intervensi jika pilot menunjukkan perlunya. Semua pilihan ini belum merupakan temuan eksperimen.

## 7. Mapping parameter uji: yang diuji apa?

| Parameter | Objek yang dinilai | Referensi/anotasi wajib | Interpretasi dan batas |
|---|---|---|---|
| Precision@k | Relevansi k item evidence hasil retrieval | Daftar record/passage relevan per query | Proporsi hasil relevan; bukan kebenaran kalimat jawaban. Tentukan aturan jika hasil kurang dari k. |
| Recall@k | Cakupan evidence relevan yang ditemukan | Himpunan gold evidence yang cukup lengkap | Bukti relevan terambil / seluruh bukti relevan. Jika gold hanya satu dokumen asal, metrik tidak membuktikan passage jawaban ditemukan. |
| F1 retrieval@k | Keseimbangan precision dan recall evidence | Gold evidence sama dengan dua metrik di atas | `2PR/(P+R)`; TP = item relevan terambil, FP = item tidak relevan terambil, FN = gold item terlewat. Laporkan macro/micro dan unit evidence. |
| MRR / nDCG@k | Urutan hasil retrieval | Relevansi biner/bertingkat yang didefinisikan | MRR menilai posisi bukti relevan pertama; nDCG menilai ranking lebih luas. Tidak sendirian memastikan semua bukti query campuran lengkap. |
| Cakupan bukti lengkap query campuran | Semua kebutuhan fakta dalam satu pertanyaan | Gold set per subpertanyaan, termasuk sumber DB dan dokumen | Proporsi query campuran yang seluruh kebutuhan buktinya tersedia. Ini endpoint operasional usulan proyek, bukan metrik universal baru yang sudah tervalidasi. |
| Akurasi fakta layanan/harga | Nilai field bisnis dalam jawaban | Snapshot database pada waktu uji; field wajib/opsional | Cocokkan layanan, angka, mata uang, satuan, syarat. Laporkan kebenaran dan kelengkapan agar sistem tidak tampak baik hanya dengan menghindari jawaban. |
| Faithfulness / claim support | Klaim jawaban didukung konteks yang benar-benar dipakai | Answer dan konteks yang persis dipakai saat generasi | Klaim didukung / klaim yang dinilai. Jawaban dapat setia pada dokumen lama tetapi tetap salah terhadap harga terkini. |
| Answer correctness / kelengkapan fakta | Kesesuaian makna jawaban dengan gold answer | Jawaban referensi beserta fakta wajib dan provenance | Pemeriksaan manual dengan rubrik dapat digunakan tanpa biaya API. Kebenaran berbeda dari sekadar relevancy. |
| Token-level answer F1 | Overlap token jawaban dan referensi | Referensi, aturan normalisasi/tokenisasi | Cocok untuk jawaban pendek tertentu; sensitif parafrasa. Ini bukan F1 retrieval dan bukan BERTScore-F1. |
| BERTScore-F1 | Kesamaan semantik token keluaran dan referensi melalui embedding | Referensi dan model BERTScore yang dicatat | Pelengkap; jawaban salah angka atau penolakan dapat tetap mirip secara semantik. Jangan dipakai sendiri untuk harga. |
| Citation precision / support | Sitasi yang mendukung pernyataan terkait | Pasangan klaim–passage dan identitas sumber | URL yang ada belum membuktikan dukungan. Tentukan cara menangani dukungan parsial/gabungan beberapa sumber. |
| Citation completeness / recall | Klaim yang memerlukan bukti mempunyai sitasi pendukung | Daftar klaim dan sumber pendukung | Dapat mengikuti definisi ALCE dengan adaptasi berbahasa Indonesia yang dijelaskan; jangan disamakan dengan recall retrieval. |
| Abstention / klarifikasi | Perilaku pada query tidak terjawab, ambigu, atau konflik | Label answerable/unanswerable/needs clarification | Laporkan penolakan benar dan penolakan keliru; penolakan berlebihan harus tampak dalam coverage. |
| Latensi dan biaya | Waktu serta sumber daya setiap query | Log retrieval, generation, total, token/panggilan model | Laporkan distribusi, misalnya median/p95 jika sampel memadai; bedakan latensi jaringan dan kegagalan layanan. |

RAGAS dapat menjadi referensi atau implementasi tambahan, tetapi penggunaan judge berbayar bukan syarat agar penelitian valid. Dengan anggaran nol, prioritaskan retrieval berlabel, verifikasi fakta database, rubrik manual, dan log yang dapat diaudit. Jika memakai judge, catat versi metrik, model, prompt, konteks, error, serta validasi sebagian terhadap penilaian manusia. Hasil satu annotator wajib diakui; jangan melaporkan inter-annotator agreement bila tidak ada pemeriksa kedua.

## 8. Rancangan eksperimen awal yang selaras dengan panduan

### RP–RQ–RO sementara

| Unsur | Rumusan calon yang perlu dikonfirmasi pilot |
|---|---|
| Research Problem (RP) | Pencarian teks tunggal berpotensi gagal menjaga ketepatan fakta operasional yang berubah sekaligus melengkapi bukti perawatan pada pertanyaan campuran. Keberadaan dan besarnya masalah pada sistem kita harus diukur. |
| RQ1 | Bagaimana perbedaan akurasi fakta bisnis dan cakupan bukti lengkap antara baseline retrieval dan sistem dengan pemilihan sumber yang eksplisit pada pertanyaan campuran? |
| RO1 | Mengevaluasi pengaruh pemilihan sumber terhadap fakta bisnis dan cakupan bukti dengan query, korpus, generator, serta budget konteks yang dikontrol. |
| RQ2 | Bagaimana perubahan dukungan klaim, kelengkapan jawaban, dan latensi setelah intervensi tersebut? |
| RO2 | Mengukur trade-off kualitas–latensi dan mengidentifikasi kategori kegagalan, tanpa mensyaratkan semua metrik naik bersamaan. |

### Baseline dan kontrol

- B1: dense retrieval atas representasi teks seluruh sumber yang diizinkan, termasuk serialisasi snapshot DB, sehingga tidak kehilangan akses data hanya karena desain pembanding.
- B2: hybrid BM25+dense atas sumber yang sama. Gunakan B2 sebagai pembanding kuat bila intervensi juga menggunakan hybrid.
- B3/ablation: DB lookup untuk fakta operasional + retrieval dokumen, dengan aturan perutean sederhana.
- Sistem usulan: satu perubahan utama yang dipilih setelah pilot, misalnya perutean sumber atau seleksi evidence berdasarkan subpertanyaan. Bila B3 sudah memenuhi masalah, jangan menambah kompleksitas tanpa alasan.

Untuk eksperimen kendali, semua sistem mendapat snapshot fakta dan korpus yang setara, pertanyaan uji sama, generator/prompt dasar sama bila memungkinkan, dan batas konteks yang sebanding. Uji pembaruan harga dibuat sebagai eksperimen terpisah dengan jadwal pembaruan/reindex yang dinyatakan; jangan membandingkan metode menggunakan informasi terbaru melawan metode yang sengaja diberi data lama lalu mengatribusikan seluruh selisih pada algoritma retrieval.

### Kategori data uji

Pertanyaan dibagi menjadi: fakta database, pengetahuan dokumen, campuran DB+dokumen, parafrasa/istilah layanan, hard negative layanan mirip, perubahan harga/sumber konflik, serta unanswerable/ambigu. Jumlah per kategori ditetapkan sebelum evaluasi final. Data pilot/development digunakan untuk memilih parameter; test final dikunci dan tidak dipakai berulang untuk memilih konfigurasi.

Setiap item minimal menyimpan `query_id`, teks, kategori, asal pertanyaan, gold answer, fakta wajib, gold record/field/passage, sumber/tanggal, answerability, dan catatan anotasi. Simpan pula konteks yang benar-benar dipakai model, output, konfigurasi, waktu, serta status eksekusi.

Skor **0 yang sah tetap disertakan**. Error API/parsing dicatat sebagai error/missing dengan denominator yang transparan; laporkan keberhasilan eksekusi dan performa end-to-end sehingga kegagalan tidak hilang dari laporan. Jangan hanya merata-ratakan pertanyaan dengan semua skor non-zero. Gunakan perbandingan berpasangan pada query yang sama dan tampilkan hasil per kategori; interval ketidakpastian digunakan bila data mendukung.

## 9. Cara mengubah mapping menjadi naskah

- **Objek:** gunakan P20/P21 untuk menjelaskan layanan salon dan pengelolaan informasi; P22/P24 hanya bila ketombe termasuk cakupan. Tambahkan bukti lokal TIEN. Jangan membuka dengan paragraf panjang tentang perkembangan teknologi.
- **Metode yang ada:** kelompokkan P01/P02/P06 untuk integrasi sumber, P03/P04/P05/P07 untuk retrieval dan preprocessing, serta P08–P11 untuk evaluasi. Related work berupa sintesis kelompok masalah, bukan 25 ringkasan berurutan.
- **Kelebihan/kekurangan:** jelaskan keterbatasan yang benar-benar relevan, misalnya dokumen-level ground truth, ketidakjelasan fakta dinamis, query campuran, atau judge bias. Bedakan keterbatasan penulis dari interpretasi kita.
- **Masalah–solusi–tujuan:** turunkan dari bukti literatur ditambah hasil pilot lokal. Klaim metode baru atau peningkatan baru hanya dibuat setelah pencarian novelty terarah dan eksperimen terkontrol.
- **Metode:** dokumentasikan korpus, izin/robots, versi data, cleaning, metadata, matching, baseline, konfigurasi, anotasi, serta definisi setiap parameter.
- **Hasil/pembahasan:** sajikan nilai per metrik/kategori dan analisis error. Hasil yang turun atau tidak berbeda tetap dibahas; jangan menyebut semua hasil bagus.
- **Judul, abstrak, simpulan:** finalisasi setelah eksperimen. Judul mengandung metode–tujuan–objek; abstrak memakai angka penelitian sendiri; simpulan menjawab RQ dalam batas data yang tersedia.

**Keputusan setelah mapping:** koleksi ini cukup untuk menyusun pilot dan kerangka eksperimen awal. Koleksi ini belum cukup untuk mengunci klaim kebaruan global atau menulis hasil penelitian sebelum eksperimen dijalankan. Prioritas berikutnya adalah bukti masalah lokal dan pilot pertanyaan campuran, disertai pencarian terarah terhadap metode yang paling dekat.

## 10. Tautan PDF lokal

Tautan di bawah mengarah ke nama PDF yang sudah ada. Seluruh PDF tetap memakai nama sebelumnya.

[P01]: <01_2026_Design-and-Evaluation-of-a-Retrieval-Augmented-Generation-LLM-Chatbot-with-Structured-Database-Access.pdf>
[P02]: <06_2026_Design-of-a-RAG-Based-Customer-Service-Chatbot-Enhanced-with-Knowledge-Graph-and-GPT-Evaluation.pdf>
[P03]: <04_2025_Lisa-a-touristic-chatbot-for-Lisbon.pdf>
[P04]: <07_2025_Design-and-Performance-Evaluation-of-LLM-Based-RAG-Pipelines-for-Chatbot-Services-in-International-Student-Admissions.pdf>
[P05]: <08_2026_Implementation-of-Retrieval-Augmented-Generation-Method-on-Large-Language-Model-for-Development-of-Campus-Service-and-Informa.pdf>
[P06]: <02_2024_Design-and-Implementation-of-an-Interactive-Question-Answering-System-with-Retrieval-Augmented-Generation-for-Personalized-Da.pdf>
[P07]: <12_2026_Evaluating-LLM-Based-Retrieval-Augmented-Generation-for-Soil-Science-Question-Answering.pdf>
[P08]: <13_2026_Efficacy-Evaluation-and-Optimization-of-RAG-Knowledge-Bases-in-the-Oil-and-Gas-Industry-Using-an-LLM-as-a-Judge-Mechanism.pdf>
[P09]: <19_2026_Evaluating-Retrieval-Augmented-Generation-A-Comprehensive-Review-of-Evaluation-Dimensions-Question-Types-and-Application.pdf>
[P10]: <26_2024_RAGAs-Automated-Evaluation-of-Retrieval-Augmented-Generation.pdf>
[P11]: <27_2023_Enabling-Large-Language-Models-to-Generate-Text-with-Citations.pdf>
[P12]: <11_2026_TechDocRAG-Relation-Preserving-Retrieval-Augmented-Generation-for-Technical-Documents.pdf>
[P13]: <10_2026_SES-RAG-An-Adaptive-Framework-with-ModernBERT-Segmentation-and-Generative-Alignment-Expansion.pdf>
[P14]: <16_2025_Retrieval-Augmented-Generation-Chatbot-for-Handling-Customer-Complaints-in-the-Energy-Sector.pdf>
[P15]: <14_2026_Dual-index-retrieval-augmented-generation-for-pedagogically-aligned-mathematics-problem-solving-support.pdf>
[P16]: <25_2025_Retrieval-Augmented-Generation.pdf>
[P17]: <20_2026_Retrieval-augmented-generation-for-natural-language-processing-a-survey.pdf>
[P18]: <22_2026_A-Survey-of-conversational-AI-from-rule-based-to-generative-and-retrieval-augmented-generation-chatbots.pdf>
[P19]: <23_2025_A-survey-on-retrieval-augmentation-generation-models-for-healthcare-applications.pdf>
[P20]: <588-597%2BJAEMB_IKE.pdf>
[P21]: <DEA%2BAMELIA%2BPUTRI%2BEDIT%2BINTERCOMS%2BDONE%2B2026.pdf>
[P22]: <1.%2BDiva%2BDaeng%2BPrayogo%2Bet%2Bal.pdf>
[P23]: <3D-Hair-Style-Recommendation-And-Salon-Scheduling.pdf>
[P24]: <10301-29624-3-PB.pdf>
[P25]: <2.%2B19257%2BAfrizal%2BFirman%2B(1).pdf>

