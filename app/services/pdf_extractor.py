import fitz

def extract_text_with_pages(pdf_path: str, max_chars: int = 20000):
    doc = fitz.open(pdf_path)
    pages = []
    total = 0
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if not text:
            continue
        if total + len(text) > max_chars:
            text = text[: max_chars - total]
            pages.append({"page": i + 1, "text": text})
            break
        pages.append({"page": i + 1, "text": text})
        total += len(text)
    full_text = "\n".join(p["text"] for p in pages)
    return {"pages": pages, "full_text": full_text}
