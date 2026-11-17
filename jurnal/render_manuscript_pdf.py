import subprocess
from pathlib import Path
import fitz

docx_path = Path(r"C:\laragon\www\RAG-salon\jurnal\manuscript_jtsiskom_rag_salon.docx")
pdf_path = Path(r"C:\laragon\www\RAG-salon\jurnal\manuscript_jtsiskom_rag_salon.pdf")
out_dir = docx_path.parent / "manuscript_pages"
out_dir.mkdir(parents=True, exist_ok=True)

cmd = [r"C:\Program Files\LibreOffice\program\soffice.exe", "--headless", "--convert-to", "pdf", str(docx_path), "--outdir", str(docx_path.parent)]
res = subprocess.run(cmd, capture_output=True, text=True)
print("LibreOffice stdout:", res.stdout)
print("LibreOffice stderr:", res.stderr)

if pdf_path.exists():
    doc = fitz.open(str(pdf_path))
    print(f"PDF successfully generated! Total pages: {len(doc)}")
    for pi, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        img_out = out_dir / f"page_{pi+1}.png"
        pix.save(str(img_out))
        print(f"  Rendered {img_out.name}")
else:
    print("PDF conversion failed.")
