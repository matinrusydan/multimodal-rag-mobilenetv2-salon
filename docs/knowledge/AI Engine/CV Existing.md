# AI Engine — CV Existing (Warisan, Offline)

Audit statis: **6 November 2026**. Modul dan model CV tersedia sebagai kode riset/inferensi, tetapi tidak aktif pada runtime web AI kanonikal.

## Batas runtime saat ini

- `apps/ai/app/main.py` melakukan `from app.rag_app import app`.
- `apps/ai/app/rag_app.py` hanya memasang router health, chat, agent, knowledge.
- `apps/api/src/routes/analyze.routes.ts` mengembalikan HTTP 503 dengan pesan fitur belum tersedia.
- `apps/ai/app/routers/analyze.py` masih ada sebagai modul, namun tidak dipasang oleh runtime aktif.

Jadi keberadaan `onnxruntime`, file model, router, ataupun test CV bukan bukti fitur analisis foto tersedia di aplikasi.

## Modul CV AI yang ditemukan

| Lokasi | Fungsi |
|---|---|
| `apps/ai/app/cv/labels.py` | Label kelas untuk prediksi. |
| `apps/ai/app/cv/preprocessing.py` | Persiapan citra untuk model. |
| `apps/ai/app/cv/model.py` | Lazy load model ONNX melalui CPUExecutionProvider. |
| `apps/ai/app/cv/hair_features.py` | Fitur citra tambahan. |
| `apps/ai/app/routers/analyze.py` | Endpoint multipart inference yang tidak terpasang di runtime aktif. |

Pipeline lama dan hasil eksperimen lebih luas berada di `apps/api/cv/{hair_type,hair_length,viewpoint,pipeline,reports,weights}`. Jangan anggap itu pipeline geometris roadmap final.

## Konsekuensi untuk pengembangan

- Ikuti `docs/08-roadmap-cv-lengkap.md` sebelum pekerjaan CV.
- Kode baru dan eksperimen roadmap diisolasi ke `apps/api/cv/geometry/` atau annotation yang ditentukan.
- Jangan menghapus atau menimpa dataset/model lama.
- Jangan membuat klaim cm absolut atau golden ratio; gunakan rasio relatif/head-unit sesuai roadmap.
- Sebelum mengaktifkan route, selesaikan gate, evaluasi, kontrak API, keamanan upload, dan validasi runtime.

Status rinci di [CV Roadmap Status](../Computer%20Vision%20Research/CV%20Roadmap%20Status.md).
