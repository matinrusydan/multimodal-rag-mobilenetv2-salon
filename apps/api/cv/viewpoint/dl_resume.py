"""
Download file model langsung dengan RESUME + RETRY + progress bar.
Bypass snapshot_download yang sering stall di file besar.
Bisa dibatalkan; bisa dijalankan ulang (lanjut dari posisi terakhir).

Pakai:
  python dl_resume.py <repo_id> <filename> <dest_path>
Contoh:
  python dl_resume.py openai/clip-vit-base-patch32 pytorch_model.bin C:\\...\\build\\model.bin
"""
import os
import sys
import time
import requests

REPO = sys.argv[1]
FNAME = sys.argv[2]
DEST = sys.argv[3]
URL = f"https://huggingface.co/{REPO}/resolve/main/{FNAME}"

os.makedirs(os.path.dirname(DEST), exist_ok=True)
print(f"[DL] {REPO}/{FNAME}", flush=True)
print(f"[DL] -> {DEST}", flush=True)

MAX_TRY = 50
for attempt in range(1, MAX_TRY + 1):
    done = os.path.getsize(DEST) if os.path.exists(DEST) else 0
    headers = {"Range": f"bytes={done}-"} if done > 0 else {}
    try:
        r = requests.get(URL, stream=True, timeout=(15, 60), headers=headers)
        if r.status_code not in (200, 206):
            print(f"[DL] HTTP {r.status_code} (coba {attempt}), tunggu...", flush=True)
            time.sleep(5)
            continue

        total = done + int(r.headers.get("Content-Length", 0))
        mode = "ab" if done > 0 else "wb"
        t0 = time.time()
        last_print = 0
        with open(DEST, mode) as f:
            for chunk in r.iter_content(1024 * 256):
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                now = time.time()
                if now - last_print >= 2:
                    last_print = now
                    speed = done / max(now - t0, 0.1) / 1e6
                    pct = (done / total * 100) if total else 0
                    print(f"[DL] {done/1e6:7.1f}/{total/1e6:.1f} MB ({pct:5.1f}%) {speed:5.2f} MB/s", flush=True)

        if total and done >= total:
            print(f"[DL] SELESAI: {done/1e6:.1f} MB", flush=True)
            sys.exit(0)
        print(f"[DL] putus di {done/1e6:.1f} MB, resume...", flush=True)

    except KeyboardInterrupt:
        print("[DL] dibatalkan user (jalankan lagi untuk lanjut).", flush=True)
        sys.exit(130)
    except Exception as e:
        print(f"[DL] coba {attempt} error: {type(e).__name__}: {e}", flush=True)
        time.sleep(3)

print("[DL] menyerah.", flush=True)
sys.exit(1)
