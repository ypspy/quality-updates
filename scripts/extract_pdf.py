# -*- coding: utf-8 -*-
"""Extract text from PDF file. Path in scripts/pdf_path.txt (UTF-8)."""
import glob
import os

def main():
    path_file = "scripts/pdf_path.txt"
    with open(path_file, encoding="utf-8") as f:
        path = f.read().strip()
    if not os.path.isfile(path):
        dirname, fname = os.path.split(path)
        parts = [p for p in fname.replace("(", " ").replace(")", " ").split() if len(p) >= 4 and p[0].isdigit()]
        pattern = (parts[0][:6] + "*.pdf") if parts else "*.pdf"
        candidates = glob.glob(os.path.join(dirname, pattern))
        path = candidates[0] if candidates else path
    from pypdf import PdfReader
    reader = PdfReader(path)
    text = ""
    for p in reader.pages:
        text += p.extract_text() or ""
    out_path = "scripts/pdf_extracted.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"OK: {out_path} ({len(text)} chars)")

if __name__ == "__main__":
    main()
