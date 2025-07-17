import os
import json
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from collections import Counter
import io

# You can customize this depending on the language of your PDFs
OCR_LANGUAGES = "eng+hin+ara"
pytesseract.pytesseract.tesseract_cmd = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")

# Basic RTL script detection (for Arabic, Hebrew, Urdu, Persian)
def is_rtl(text):
    for char in text:
        if '\u0600' <= char <= '\u06FF' or '\u0590' <= char <= '\u05FF':
            return True
    return False

# OCR text from scanned PDF page image
def extract_text_from_image(page):
    pix = page.get_pixmap(dpi=300)
    image_bytes = pix.tobytes("png")
    image = Image.open(io.BytesIO(image_bytes))
    text = pytesseract.image_to_string(image, lang=OCR_LANGUAGES)
    return text

# Main function
def extract_outline_from_pdf(filepath):
    doc = fitz.open(filepath)
    headings = []
    font_stats = Counter()
    title = ""
    max_fontsize = 0
    seen_headings = set()

    # Pass 1: Gather font sizes and detect largest text as title
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        if not blocks or all("lines" not in block for block in blocks):
            continue  # Skip for now, handled in pass 2

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    font_size = span["size"]
                    if not text or len(text) <= 2:
                       continue
                    if text.isdigit() and len(text) <= 2:
                       continue  
                    font_stats[round(font_size, 1)] += 1
                    if font_size > max_fontsize:
                        max_fontsize = font_size
                        title = text

    # Define heading levels from font stats
    sizes_sorted = sorted(font_stats.keys(), reverse=True)
    h1_size = sizes_sorted[0] if len(sizes_sorted) > 0 else max_fontsize
    h2_size = sizes_sorted[1] if len(sizes_sorted) > 1 else h1_size * 0.85
    h3_size = sizes_sorted[2] if len(sizes_sorted) > 2 else h1_size * 0.70

    # Pass 2: Extract headings (with OCR fallback if needed)
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")["blocks"]

        # 🔁 If no real text blocks, do OCR
        if not blocks or all("lines" not in b for b in blocks):
            ocr_text = extract_text_from_image(page)
            for line in ocr_text.split("\n"):
                line = line.strip()
                if len(line) < 3:
                    continue
                if is_rtl(line):
                    line = line[::-1]
                if line in seen_headings:
                    continue
                seen_headings.add(line)
                headings.append({
                    "level": "H3",  # Default for OCR text
                    "text": line,
                    "page": page_num
                })
            continue

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    font_size = round(span["size"], 1)

                    if not text or len(text) <= 2:
                        continue
                    if text.isdigit() and len(text) <= 2:
                       continue  
                    # if text in seen_headings:
                    #     continue
                    # seen_headings.add(text)

                    if is_rtl(text):
                        text = text[::-1]

                    level = None
                    if font_size >= h1_size:
                        level = "H1"
                    elif font_size >= h2_size:
                        level = "H2"
                    elif font_size >= h3_size:
                        level = "H3"

                    if level:
                        headings.append({
                            "level": level,
                            "text": text,
                            "page": page_num
                        })

    # Handle RTL title too
    clean_title = title[::-1] if is_rtl(title) else title

    return {
        "title": clean_title,
        "outline": headings
    }


def main():
    input_dir =  os.path.join(os.getcwd(), 'input')
    output_dir = os.path.join(os.getcwd(), 'output')

    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".pdf"):
            input_path = os.path.join(input_dir, filename)
            result = extract_outline_from_pdf(input_path)
            output_filename = os.path.splitext(filename)[0] + ".json"
            output_path = os.path.join(output_dir, output_filename)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2,ensure_ascii=False)

if __name__ == "__main__":
    print("Starting processing pdfs")
    main()
    print("completed processing pdfs")

    # docker run --rm -v "${PWD}/input:/app/input" -v "${PWD}/output:/app/output" --network none myapp