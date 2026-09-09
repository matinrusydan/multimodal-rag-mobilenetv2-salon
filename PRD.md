# Product Requirements Document (PRD)

## Sistem Konsultasi Virtual Salon Berbasis Multimodal RAG dengan Klasifikasi Citra Rambut Menggunakan MobileNetV2

**Versi:** 1.0
**Tanggal:** 8 September 2026
**Status:** Draft
**Penulis:** Mahasiswa Teknik Informatika, Universitas Siliwangi

---

## Daftar Isi

1. [Ringkasan Proyek](#1-ringkasan-proyek)
2. [Tujuan & Target Pengguna](#2-tujuan--target-pengguna)
3. [Fitur Utama](#3-fitur-utama)
4. [Arsitektur Sistem](#4-arsitektur-sistem)
5. [Spesifikasi Backend](#5-spesifikasi-backend)
6. [Spesifikasi Frontend](#6-spesifikasi-frontend)
7. [Data & Dataset](#7-data--dataset)
8. [Spesifikasi API](#8-spesifikasi-api)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Rencana Implementasi](#10-rencana-implementasi)
11. [Metrik Keberhasilan](#11-metriks-keberhasilan)
12. [Risiko & Mitigasi](#12-risiko--mitigasi)
13. [Glossary](#13-glossary)

---

## 1. Ringkasan Proyek

### 1.1 Problem Statement

Industri salon kecantikan di Indonesia masih mengandalkan konsultasi konvensional. Pelanggan harus datang langsung untuk mengetahui harga (yang bergantung pada panjang rambut) dan mendapatkan rekomendasi gaya potongan. Belum ada sistem yang mengintegrasikan analisis foto rambut dengan chatbot konsultasi untuk memberikan estimasi harga dan rekomendasi personalisasi secara otomatis.

### 1.2 Solusi

Membangun sistem web yang menggabungkan:
- **Computer Vision (MobileNetV2)** untuk mengklasifikasikan panjang dan jenis rambut dari foto
- **RAG (Retrieval-Augmented Generation)** untuk chatbot konsultasi yang mengambil informasi dari knowledge base salon
- **Integrasi Multimodal** di mana hasil CV menjadi konteks bagi RAG dalam menghasilkan respons

### 1.3 Ruang Proyek

| Item | Scope |
|---|---|
| Platform | Web application (responsive) |
| Bahasa | Bahasa Indonesia |
| Domain | Layanan salon kecantikan |
| Skala | Prototype / Proof of Concept untuk skripsi |
| Deployment | Lokal / Cloud (Render / Vercel) |

---

## 2. Tujuan & Target Pengguna

### 2.1 Tujuan Proyek

| # | Tujuan | Ukuran Keberhasilan |
|---|---|---|
| T1 | Klasifikasi panjang rambut (4 kelas) | Akurasi ≥ 85% |
| T2 | Klasifikasi jenis rambut (4 kelas) | Akurasi ≥ 85% |
| T3 | Chatbot konsultasi berbasis RAG | Faithfulness RAGAS ≥ 0.80 |
| T4 | Estimasi harga otomatis dari foto | Harga sesuai kelas panjang rambut |
| T5 | Rekomendasi gaya berdasarkan jenis rambut | Minimal 3 rekomendasi per query |
| T6 | User Acceptance Testing | Kepuasan ≥ 4.0 / 5.0 |

### 2.2 Target Pengguna

| User Type | Deskripsi | Kebutuhan Utama |
|---|---|---|
| **Pelanggan Salon** | Orang yang ingin konsultasi potong rambut | Upload foto → tahu harga & dapat rekomendasi gaya |
| **Pemilik Salon** | Pemilik usaha salon kecantikan | Digitalisasi layanan konsultasi |

---

## 3. Fitur Utama

### 3.1 Fitur MVP (Minimum Viable Product)

#### F1: Upload Foto Rambut
- Pengguna dapat mengunggah foto rambut (jpg/png, max 5MB)
- Sistem menampilkan preview foto sebelum diproses
- Crop/resize otomatis ke 224x224px

#### F2: Klasifikasi Rambut via CV
- Sistem menganalisis foto dan menghasilkan:
  - **Panjang rambut**: pendek, pendek-menengah, menengah, panjang
  - **Jenis rambut**: lurus, bergelombang, keriting, sangat keriting
  - **Confidence score** per kelas (0-100%)
- Hasil ditampilkan ke pengguna dengan visualisasi

#### F3: Chatbot Konsultasi
- Interface chat seperti messaging app
- Pengguna bisa bertanya dalam Bahasa Indonesia
- Chatbot memahami konteks percakapan (multi-turn)
- Pengguna bisa mengirim foto + teks secara bersamaan

#### F4: Rekomendasi Gaya Rambut
- Berdasarkan jenis rambut terdeteksi, sistem merekomendasikan minimal 3 gaya
- Setiap rekomendasi dilengkapi: nama gaya, deskripsi, foto referensi (opsional)
- Rekomendasi diambil dari knowledge base (RAG)

#### F5: Estimasi Harga
- Berdasarkan panjang rambut terdeteksi, sistem menampilkan estimasi harga
- Harga disesuaikan dengan jenis layanan (potong, cat, treatment)
- Format: "Potong rambut [panjang]: Rp XX.000 - Rp XX.000"

#### F6: Tips Perawatan
- Chatbot memberikan tips perawatan berdasarkan jenis rambut
- Informasi diambil dari knowledge base

#### F7: Booking (Basic)
- Menampilkan informasi kontak salon
- Link ke WhatsApp / form booking sederhana

### 3.2 Fitur Nice-to-Have (v2)

| Fitur | Prioritas | Keterangan |
|---|---|---|
| Riwayat percakapan | Medium | Simpan history chat |
| Face shape detection | Low | Tambah rekomendasi berdasarkan bentuk wajah |
| Virtual try-on | Low | Overlay gaya rambut pada foto |
| Multi-bahasa | Low | English mode |
| Rating & feedback | Medium | Pengguna menilai kualitas rekomendasi |

---

## 4. Arsitektur Sistem

### 4.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLIENT (Browser)                         │
│                                                               │
│  ┌──────────────────┐    ┌────────────────────────────────┐  │
│  │   React App       │    │   Tailwind CSS                 │  │
│  │   - PhotoUpload   │    │   - Responsive Design          │  │
│  │   - ChatInterface │    │   - Mobile-first               │  │
│  │   - ResultCard    │    │                                │  │
│  └────────┬─────────┘    └────────────────────────────────┘  │
└───────────┼──────────────────────────────────────────────────┘
            │ HTTP / WebSocket
            ↓
┌─────────────────────────────────────────────────────────────┐
│                    SERVER (FastAPI)                           │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  API Layer (main.py)                                    │ │
│  │  - POST /api/analyze        (upload foto → hasil CV)    │ │
│  │  - POST /api/chat           (kirim chat → respons RAG)  │ │
│  │  - GET  /api/knowledge      (lihat knowledge base)      │ │
│  │  - GET  /api/health         (health check)              │ │
│  └───────────┬─────────────────────────────────────────────┘ │
│              ↓                                               │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  CV Pipeline          │  │  RAG Pipeline                │ │
│  │  (model.py)           │  │  (chatbot.py)                │ │
│  │                       │  │                               │ │
│  │  - Preprocessing      │  │  - Embedding                  │ │
│  │  - MobileNetV2        │  │  - ChromaDB Query             │ │
│  │  - Postprocessing     │  │  - Prompt Builder             │ │
│  │  - Label Mapping      │  │  - LLM Call (GPT-4o-mini)     │ │
│  └───────────┬──────────┘  └──────────────┬───────────────┘ │
│              ↓                             ↓                  │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │  Model Weights        │  │  Vector Database              │ │
│  │  (weights/)           │  │  (ChromaDB)                   │ │
│  │  - hair_length.pt     │  │  - embeddings/                │ │
│  │  - hair_type.pt       │  │  - metadata/                  │ │
│  └──────────────────────┘  └──────────────────────────────┘ │
│              ↓                             ↓                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Knowledge Base (knowledge/)                             │ │
│  │  - harga.md                                             │ │
│  │  - layanan.md                                           │ │
│  │  - gaya-rambut.md                                       │ │
│  │  - tips-perawatan.md                                    │ │
│  │  - booking-info.md                                      │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Data Flow

```
User Upload Foto
       │
       ↓
[1] Preprocessing (resize 224x224, normalize)
       │
       ↓
[2] MobileNetV2 Inference
       │
       ├──→ Panjang: "menengah" (confidence: 92%)
       └──→ Jenis: "bergelombang" (confidence: 88%)
       │
       ↓
[3] Prompt Builder
       │
       ├──→ Gabung: hasil CV + query user + retrieved docs
       │
       ↓
[4] RAG Pipeline
       │
       ├──→ Embedding query → ChromaDB similarity search → top-5 docs
       │
       ├──→ Kirim ke GPT-4o-mini dengan context
       │
       ↓
[5] Response Generator
       │
       ├──→ "Rambut Anda terdeteksi: panjang menengah, bergelombang."
       ├──→ "Cocok untuk: Layer Shaggy (Rp 75.000), Curtain Bangs (Rp 80.000)..."
       ├──→ "Tips: Gunakan conditionernya setiap habis keramas..."
       │
       ↓
User Menerima Respons
```

---

## 5. Spesifikasi Backend

### 5.1 Tech Stack

| Komponen | Teknologi | Versi | Alasan |
|---|---|---|---|
| **Runtime** | Python | 3.10+ | Standar untuk ML/DL |
| **Web Framework** | FastAPI | 0.110+ | Async, cepat, auto-docs |
| **CV Model** | PyTorch + MobileNetV2 | 2.0+ | Transfer learning, ringan |
| **LLM** | OpenAI GPT-4o-mini | — | Murah, cepat, bagus untuk Bahasa Indonesia |
| **Embedding** | text-embedding-3-small | — | Murah, 1536 dimensi |
| **Vector DB** | ChromaDB | 0.4+ | Ringan, cocok untuk prototype |
| **Image Processing** | Pillow + torchvision | — | Standar |

### 5.2 CV Pipeline

```
Input: Foto (any resolution)
  ↓
Resize → 224 x 224
  ↓
Normalize → mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
  ↓
ToTensor → [1, 3, 224, 224]
  ↓
MobileNetV2 (pre-trained, fine-tuned)
  ↓
Output → Softmax probabilities
  ↓
Postprocessing → Label + Confidence
```

**Model Configuration:**

| Parameter | Nilai |
|---|---|
| Backbone | MobileNetV2 (pre-trained ImageNet) |
| Input Size | 224 x 224 x 3 |
| Fine-tuning | Freeze 60% layer awal, unfreeze 40% akhir |
| Optimizer | Adam (lr=0.001) |
| Loss | CrossEntropyLoss |
| Output Panjang | 4 kelas: pendek, pendek-menengah, menengah, panjang |
| Output Jenis | 4 kelas: lurus, bergelombang, keriting, sangat keriting |
| Confidence Threshold | 50% (di bawah ini → "tidak yakin") |

### 5.3 RAG Pipeline

```
Input: Query (teks) + Hasil CV (konteks)
  ↓
Prompt Construction
  ↓
Embedding Query → Vector [1, 1536]
  ↓
ChromaDB Similarity Search (top_k=5)
  ↓
Retrieve Documents → [doc1, doc2, doc3, doc4, doc5]
  ↓
Format Prompt:
  System: "Anda adalah konsultan salon..."
  Context: [retrieved docs]
  User Input: [hasil CV + query]
  ↓
GPT-4o-mini → Generated Response
  ↓
Postprocessing (hapus artifact, format)
  ↓
Output: Respons konsultasi
```

**RAG Configuration:**

| Parameter | Nilai |
|---|---|
| Embedding Model | text-embedding-3-small (OpenAI) |
| Vector DB | ChromaDB (persistent) |
| Chunk Size | 500-1000 tokens |
| Chunk Overlap | 100 tokens |
| Similarity Metric | Cosine |
| Top-K Retrieved | 5 |
| LLM | GPT-4o-mini |
| Temperature | 0.7 |
| Max Tokens | 1000 |

---

## 6. Spesifikasi Frontend

### 6.1 Tech Stack

| Komponen | Teknologi | Versi |
|---|---|---|
| **Framework** | React | 18+ |
| **Build Tool** | Vite | 5+ |
| **Styling** | Tailwind CSS | 3+ |
| **HTTP Client** | Axios / Fetch API | — |
| **Icons** | Lucide React | — |

### 6.2 Halaman

| Halaman | Route | Deskripsi |
|---|---|---|
| **Home** | `/` | Landing page + mulai konsultasi |
| **Consult** | `/consult` | Interface utama: upload foto + chat |
| **About** | `/about` | Tentang aplikasi |

### 6.3 Komponen Utama

#### PhotoUpload
- Drag & drop area atau click untuk upload
- Preview foto sebelum kirim
- Validasi: max 5MB, jpg/png only
- Loading spinner saat upload

#### ChatInterface
- Bubble chat layout (user di kanan, bot di kiri)
- Input teks + tombol upload foto
- Auto-scroll ke pesan terbaru
- Typing indicator saat bot memproses

#### ResultCard
- Menampilkan hasil klasifikasi CV
- Confidence bar per kelas
- Warna: hijau untuk confidence tinggi, kuning untuk sedang, merah untuk rendah

#### RecommendationCard
- Menampilkan rekomendasi gaya rambut
- Nama gaya + deskripsi singkat
- Estimasi harga
- Tombol "Pilih" (opsional)

### 6.4 Responsive Breakpoints

| Breakpoint | Lebar | Layout |
|---|---|---|
| Mobile | < 640px | Single column, full-width chat |
| Tablet | 640-1024px | Side-by-side (foto + chat) |
| Desktop | > 1024px | Three-column (sidebar + chat + results) |

---

## 7. Data & Dataset

### 7.1 Dataset Training CV

#### Sumber Data

| Sumber | URL | Ketersediaan | Catatan |
|---|---|---|---|
| Hair Type Dataset (Kaggle) | kaggle.com/datasets/klatzswe/long-hair-dataset | Public | Perlu anotasi ulang |
| Long Hair Dataset (Kaggle) | kaggle.com/datasets | Public | Binary (long/short) |
| Foto Sendiri | — | Buat sendiri | Perlu izin partisipan |

#### Struktur Dataset

```
data/
├── train/
│   ├── length/
│   │   ├── pendek/          (150-200 images)
│   │   ├── pendek-menengah/ (150-200 images)
│   │   ├── menengah/        (150-200 images)
│   │   └── panjang/         (150-200 images)
│   └── type/
│       ├── lurus/           (150-200 images)
│       ├── bergelombang/    (150-200 images)
│       ├── keriting/        (150-200 images)
│       └── sangat-keriting/ (150-200 images)
├── val/
│   └── (struktur sama, 10% dari total)
└── test/
    └── (struktur sama, 10% dari total)
```

#### Anotasi

| Field | Tipe | Contoh |
|---|---|---|
| image_id | string | IMG_001 |
| filename | string | IMG_001.jpg |
| hair_length | string | "menengah" |
| hair_type | string | "bergelombang" |
| confidence_notes | string | "rambut sebahu, bergelombang ringan" |

### 7.2 Knowledge Base (RAG)

#### Struktur Knowledge Base

```
knowledge/
├── harga.md
├── layanan.md
├── gaya-rambut.md
├── tips-perawatan.md
└── booking-info.md
```

#### Format Dokumen (Contoh: harga.md)

```markdown
# Daftar Harga Layanan Salon

## Potong Rambut
| Panjang | Harga Normal | Harga VIP |
|---------|-------------|-----------|
| Pendek | Rp 35.000 - Rp 50.000 | Rp 60.000 |
| Pendek-Menengah | Rp 40.000 - Rp 55.000 | Rp 70.000 |
| Menengah | Rp 45.000 - Rp 65.000 | Rp 85.000 |
| Panjang | Rp 55.000 - Rp 80.000 | Rp 100.000 |

## Cat Rambut
| Panjang | Harga Normal |
|---------|-------------|
| Pendek | Rp 100.000 - Rp 150.000 |
| Pendek-Menengah | Rp 120.000 - Rp 180.000 |
| Menengah | Rp 150.000 - Rp 250.000 |
| Panjang | Rp 200.000 - Rp 350.000 |

## Treatment
| Layanan | Harga | Durasi |
|---------|-------|--------|
| Hair Spa | Rp 50.000 - Rp 80.000 | 30 menit |
| Creambath | Rp 60.000 - Rp 90.000 | 45 menit |
| Smoothing | Rp 200.000 - Rp 500.000 | 2-3 jam |
| Keratin Treatment | Rp 300.000 - Rp 700.000 | 2-3 jam |
```

---

## 8. Spesifikasi API

### 8.1 Endpoint

#### POST /api/analyze

Upload foto → dapat hasil klasifikasi CV.

**Request:**
```
Content-Type: multipart/form-body

file: <binary image>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "hair_length": {
      "label": "menengah",
      "confidence": 0.92,
      "all_scores": {
        "pendek": 0.03,
        "pendek-menengah": 0.05,
        "menengah": 0.92,
        "panjang": 0.00
      }
    },
    "hair_type": {
      "label": "bergelombang",
      "confidence": 0.88,
      "all_scores": {
        "lurus": 0.05,
        "bergelombang": 0.88,
        "keriting": 0.06,
        "sangat-keriting": 0.01
      }
    },
    "processing_time_ms": 145
  }
}
```

#### POST /api/chat

Kirim pesan (teks + context CV) → dapat respons chatbot.

**Request:**
```json
{
  "message": "Gaya rambut apa yang cocok untuk saya?",
  "hair_context": {
    "hair_length": "menengah",
    "hair_type": "bergelombang",
    "confidence_length": 0.92,
    "confidence_type": 0.88
  },
  "conversation_id": "optional-conversation-id"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "response": "Berdasarkan analisis, rambut Anda berjenis bergelombang dengan panjang menengah. Gaya yang sangat cocok untuk Anda adalah:\n\n1. **Layer Shaggy** - Memberikan tekstur alami pada rambut bergelombang...\n2. **Curtain Bangs** - Poni belah tengah yang menyeimbangkan bentuk wajah...\n3. **Soft Wave Bob** - Potongan bob dengan gelombang natural...\n\nUntuk harga potong rambut menengah, estimasi kami Rp 45.000 - Rp 65.000.",
    "sources": [
      {"doc": "gaya-rambut.md", "relevance": 0.95},
      {"doc": "harga.md", "relevance": 0.87}
    ],
    "conversation_id": "conv_abc123",
    "processing_time_ms": 2340
  }
}
```

#### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "cv_model_loaded": true,
  "rag_ready": true,
  "knowledge_base_docs": 25
}
```

---

## 9. Non-Functional Requirements

### 9.1 Performance

| Metrik | Target |
|---|---|
| CV Inference Time | < 500ms per gambar |
| RAG Response Time | < 5 detik total |
| API Response Time | < 3 detik (end-to-end) |
| Frontend Load Time | < 2 detik (initial) |
| Model Size | < 50MB (CV model) |

### 9.2 Reliability

| Metrik | Target |
|---|---|
| Uptime | 95% (untuk prototype) |
| Error Rate | < 5% |
| Graceful Degradation | Jika CV gagal, tetap bisa chat tanpa foto |

### 9.3 Security

| Aspek | Implementasi |
|---|---|
| API Key Safety | Simpan di `.env`, jangan commit ke git |
| File Upload | Validasi tipe dan ukuran file |
| Rate Limiting | Max 10 request/menit per IP (opsional) |
| CORS | Whitelist domain frontend saja |

### 9.4 Usability

| Aspek | Target |
|---|---|
| Mobile Friendly | Responsif di semua ukuran layar |
| Loading Indicator | Tampilkan spinner saat proses |
| Error Message | Pesan error dalam Bahasa Indonesia |
| Accessibility | Alt text untuk gambar, semantic HTML |

---

## 10. Rencana Implementasi

### 10.1 Phase 1: Setup & Knowledge Base (Hari 1-2)

| Tugas | Output | Estimasi |
|---|---|---|
| Setup project structure | Folder backend + frontend | 1 jam |
| Setup Python environment | requirements.txt, venv | 30 menit |
| Setup React + Vite + Tailwind | Project frontend jalan | 1 jam |
| Buat knowledge base (.md) | 5 file knowledge | 2 jam |
| Setup ChromaDB + embedding | Vector DB berjalan | 1 jam |
| Test RAG pipeline (manual) | Chatbot bisa jawab pertanyaan | 2 jam |

### 10.2 Phase 2: CV Pipeline (Hari 3-5)

| Tugas | Output | Estimasi |
|---|---|---|
| Kumpulkan/gabung dataset | Dataset terstruktur | 4 jam |
| Anotasi dataset | Label panjang + jenis | 4 jam |
| Training MobileNetV2 | Model terlatih | 3 jam |
| Evaluasi model | Classification report | 1 jam |
| Export model (.pth) | Model file siap pakai | 30 menit |
| Integrasikan ke FastAPI | Endpoint /api/analyze | 2 jam |

### 10.3 Phase 3: RAG Pipeline (Hari 6-7)

| Tugas | Output | Estimasi |
|---|---|---|
| Indexing knowledge base | ChromaDB terisi | 1 jam |
| Build prompt template | Template siap pakai | 1 jam |
| Integrasi GPT-4o-mini | Chatbot berjalan | 2 jam |
| Test multi-turn conversation | Context-aware chat | 1 jam |
| Integrasi CV + RAG | Multimodal pipeline | 2 jam |

### 10.4 Phase 4: Frontend (Hari 8-10)

| Tugas | Output | Estimasi |
|---|---|---|
| PhotoUpload component | Upload + preview | 2 jam |
| ChatInterface component | Chat bubble layout | 3 jam |
| ResultCard component | Tampilkan hasil CV | 1 jam |
| RecommendationCard component | Tampilkan rekomendasi | 1 jam |
| Responsive design | Mobile-friendly | 2 jam |
| Connect ke backend API | End-to-end flow | 2 jam |

### 10.5 Phase 5: Testing & Evaluasi (Hari 11-12)

| Tugas | Output | Estimasi |
|---|---|---|
| RAGAS evaluation | Skor faithfulness, relevancy | 2 jam |
| User Acceptance Testing | Kuesioner terisi | 2 jam |
| Bug fixing | Stable version | 2 jam |
| Dokumentasi | README, setup guide | 1 jam |

---

## 11. Metrik Keberhasilan

### 11.1 CV Metrics

| Metrik | Target | Tool |
|---|---|---|
| Accuracy (panjang) | ≥ 85% | sklearn.metrics |
| Accuracy (jenis) | ≥ 85% | sklearn.metrics |
| F1-Score (macro) | ≥ 0.85 | sklearn.metrics |
| Confusion Matrix | Visualisasi | matplotlib/seaborn |
| Inference Time | < 500ms | time.time() |

### 11.2 RAG Metrics

| Metrik | Target | Tool |
|---|---|---|
| Faithfulness | ≥ 0.80 | RAGAS |
| Answer Relevancy | ≥ 0.75 | RAGAS |
| Context Precision | ≥ 0.70 | RAGAS |
| Context Recall | ≥ 0.70 | RAGAS |
| Response Time | < 5s | time.time() |

### 11.3 User Experience Metrics

| Metrik | Target | Tool |
|---|---|---|
| Kepuasan (Likert 1-5) | ≥ 4.0 | Kuesioner |
| Kemudahan Penggunaan | ≥ 4.0 | Kuesioner |
| Akurasi Rekomendasi | ≥ 4.0 | Kuesioner |
| NPS (Net Promoter Score) | ≥ 50 | Kuesioner |

---

## 12. Risiko & Mitigasi

| # | Risiko | Probabilitas | Dampak | Mitigasi |
|---|---|---|---|---|
| 1 | Dataset kurang/tidak representatif | Tinggi | Tinggi | Gabung beberapa sumber + augmentasi data |
| 2 | Akurasi CV di bawah target | Sedang | Tinggi | Tuning hyperparameter, coba backbone lain |
| 3 | GPT-4o-mini halusinasi | Sedang | Sedang | RAGAS evaluation, prompt engineering ketat |
| 4 | Biaya API OpenAI tinggi | Rendah | Sedang | Gunakan GPT-4o-mini (murah), cache respons |
| 5 | Integration bug CV + RAG | Sedang | Sedang | Unit test tiap komponen, test pipeline end-to-end |
| 6 | Frontend tidak responsive | Rendah | Rendah | Mobile-first design, test di berbagai device |

---

## 13. Glossary

| Istilah | Definisi |
|---|---|
| **RAG** | Retrieval-Augmented Generation — arsitektur yang menggabungkan retrieval informasi dengan generasi teks oleh LLM |
| **MobileNetV2** | Arsitektur CNN ringan yang dirancang untuk efisiensi pada perangkat mobile |
| **Transfer Learning** | Teknik menggunakan model yang sudah dilatih pada dataset lain sebagai titik awal |
| **ChromaDB** | Vector database untuk menyimpan dan mencari embeddings |
| **Embedding** | Representasi vektor dari teks/gambar dalam ruang berdimensi tinggi |
| **Fine-tuning** | Melatih ulang sebagian layer model pada dataset baru |
| **Confidence Score** | Probabilitas/kepastian model terhadap prediksinya |
| **Knowledge Base** | Kumpulan dokumen informasi yang digunakan oleh sistem RAG |
| **UAT** | User Acceptance Testing — pengujian oleh pengguna akhir |
| **RAGAS** | Framework evaluasi untuk sistem RAG |
| **LLM** | Large Language Model — model bahasa berukuran besar |
| **Prompt Builder** | Modul yang menyusun prompt untuk LLM dari berbagai input |
| **Multimodal** | Sistem yang memproses lebih dari satu tipe data (teks, gambar, dll) |
| **Endpoint** | URL spesifik pada API yang melayani request tertentu |

---

## Lampiran

### A. Struktur File Proyek

```
salon-consultant/
├── backend/
│   ├── main.py                    # FastAPI app
│   ├── cv/
│   │   ├── model.py               # MobileNetV2 pipeline
│   │   ├── train.py               # Training script
│   │   ├── evaluate.py            # Evaluation script
│   │   └── weights/
│   │       ├── hair_length.pth
│   │       └── hair_type.pth
│   ├── rag/
│   │   ├── knowledge_base.py      # ChromaDB setup
│   │   ├── embeddings.py          # Embedding pipeline
│   │   └── chatbot.py             # RAG + LLM
│   ├── knowledge/
│   │   ├── harga.md
│   │   ├── layanan.md
│   │   ├── gaya-rambut.md
│   │   ├── tips-perawatan.md
│   │   └── booking-info.md
│   ├── data/
│   │   ├── train/
│   │   ├── val/
│   │   └── test/
│   ├── tests/
│   │   ├── test_cv.py
│   │   ├── test_rag.py
│   │   └── test_api.py
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── PhotoUpload.jsx
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── ResultCard.jsx
│   │   │   ├── RecommendationCard.jsx
│   │   │   └── Header.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   └── Consult.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── docs/
│   ├── proposal-skripsi.md
│   └── PRD.md
├── .gitignore
└── README.md
```

### B. Environment Variables

```env
# Backend (.env)
OPENAI_API_KEY=sk-your-api-key-here
CHROMA_PERSIST_DIR=./chroma_db
MODEL_LENGTH_PATH=./cv/weights/hair_length.pth
MODEL_TYPE_PATH=./cv/weights/hair_type.pth
HOST=0.0.0.0
PORT=8000
DEBUG=true

# Frontend (.env)
VITE_API_URL=http://localhost:8000
```

### C. Requirements (Python)

```
fastapi==0.110.0
uvicorn==0.27.0
python-multipart==0.0.9
torch==2.2.0
torchvision==0.17.0
Pillow==10.2.0
openai==1.12.0
chromadb==0.4.22
langchain==0.1.9
ragas==0.1.4
scikit-learn==1.4.0
numpy==1.26.4
python-dotenv==1.0.1
```

### D. Package.json (Frontend)

```json
{
  "name": "salon-consultant-frontend",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.7",
    "lucide-react": "^0.323.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "vite": "^5.1.0",
    "tailwindcss": "^3.4.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35"
  }
}
```

---

**Dokumen ini akan diperbarui seiring implementasi berlangsung.**
