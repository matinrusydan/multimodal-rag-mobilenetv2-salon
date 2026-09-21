"""
Downloader model CLIP yang tahan putus: retry + resume + log jelas.
Tidak akan nyangkut tanpa output.

Pakai:
  python hf_dl.py openai/clip-vit-base-patch32
"""
import sys
import time
import traceback

MODEL = sys.argv[1] if len(sys.argv) > 1 else "openai/clip-vit-base-patch32"

print(f"[DL] Mulai unduh: {MODEL}", flush=True)

from huggingface_hub import snapshot_download, constants

print(f"[DL] Cache dir: {constants.HF_HUB_CACHE}", flush=True)

MAX_TRY = 20
for attempt in range(1, MAX_TRY + 1):
    try:
        print(f"[DL] Percobaan {attempt}/{MAX_TRY} ...", flush=True)
        t0 = time.time()
        path = snapshot_download(
            MODEL,
            # hanya file yang dibutuhkan; JANGAN sebut safetensors utk clip-base (tidak ada -> 404)
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onnx", "*.tflite"],
            max_workers=1,
            etag_timeout=30,
        )
        dt = time.time() - t0
        print(f"[DL] SELESAI dalam {dt:.1f}s -> {path}", flush=True)
        sys.exit(0)
    except KeyboardInterrupt:
        print("[DL] Dibatalkan user.", flush=True)
        sys.exit(130)
    except Exception as e:
        print(f"[DL] GAGAL percobaan {attempt}: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        wait = min(5 * attempt, 30)
        print(f"[DL] Tunggu {wait}s lalu ulang (resume otomatis)...", flush=True)
        time.sleep(wait)

print("[DL] HABIS percobaan, menyerah.", flush=True)
sys.exit(1)
