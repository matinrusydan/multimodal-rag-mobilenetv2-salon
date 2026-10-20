# Baseline BM25 — curated development v1

13 evidence, 24 pertanyaan. Top-5; BM25 k1=1,5 dan b=0,75. Tidak ada API, generasi, atau perubahan index.

Acuan dan pemetaan bukti baru masih kandidat. Pemeriksaan otomatis memastikan ID, sumber, kebijakan dan hash konsisten; bukan pengganti penilaian semantik manusia.

| Kategori | Dinilai/total | Precision | Recall | F1 retrieval | Bukti lengkap |
|---|---|---|---|---|---|
| all | 20/24 | 0.240 | 0.975 | 0.376 | 0.950 |
| business_and_clarification | 1/1 | 0.200 | 1.000 | 0.333 | 1.000 |
| business_and_policy | 1/1 | 0.200 | 1.000 | 0.333 | 1.000 |
| business_and_source_gap | 1/1 | 0.200 | 1.000 | 0.333 | 1.000 |
| clarification | 0/1 | NA | NA | NA | NA |
| database | 6/6 | 0.200 | 1.000 | 0.333 | 1.000 |
| difficult | 3/4 | 0.267 | 1.000 | 0.413 | 1.000 |
| document | 5/5 | 0.200 | 1.000 | 0.333 | 1.000 |
| mixed | 3/3 | 0.400 | 0.833 | 0.536 | 0.667 |
| policy_boundary | 0/1 | NA | NA | NA | NA |
| source_gap | 0/1 | NA | NA | NA | NA |

## Kegagalan menemukan kelompok bukti

### r18

Berapa harga serta durasi Volume Blowout Styling dan isi panduan untuk rambut kering?

Kelompok terlewat: [["care:S01:conditioner-by-hair-type:v1"]]

Urutan bukti gold: {"care:S01:conditioner-by-hair-type:v1": 9, "db:services:6": 1}

Top-k: Volume Blowout Styling, Precision Haircut, Mengurai kusut pada rambut keriting, Keratin Smooth Treatment, Membatasi panas saat styling.


## Batas interpretasi

Precision adalah proporsi ID gold dalam evidence yang diambil; recall adalah proporsi ID gold terambil. F1 retrieval dihitung per pertanyaan lalu dirata-ratakan. Kelengkapan bernilai 1 jika setiap kelompok wajib terwakili. Saat ini seluruh kelompok berisi satu ID.

r08, r20, r21 dan r22 tidak memiliki gold retrieval dan dikeluarkan dari denominator; tidak dinyatakan berhasil. Kepatuhan kebijakan, klarifikasi, penolakan resep, dan abstention belum diuji. Kasus partial hanya menilai kebutuhan faktual yang didukung, misalnya harga; skor tinggi tidak membuktikan saran sampo atau instruksi perawatan khusus benar.

Seluruh teks kandidat diperingkatkan, tetapi cuplikan hasil dibatasi 400 karakter per evidence. Hit pada ID tidak memverifikasi setiap klaim dalam cuplikan. Atribut expected_business_facts dapat memuat field konteks yang tidak diminta pertanyaan; jangan menghukum jawaban karena tidak menyebut field yang tidak ditanyakan.

Korpus kecil dan diseleksi berdasarkan inspeksi development. Jangan membandingkan skor ini dengan pilot lama sebagai efek peningkatan algoritma, karena korpus dan label berubah. Tidak ada keluaran neural dense, RAGAS, faithfulness, atau akurasi jawaban yang dibuat dari tes ini.

Langkah berikut: audit error per pertanyaan dan bukti alternatif; perluas korpus/keluarga pertanyaan; tinjau pemetaan sebelum pembekuan gold. Jika menjalankan variasi algoritma, gunakan korpus/pertanyaan/budget yang sama dan pisahkan test final.
