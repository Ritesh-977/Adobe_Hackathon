import fitz  # PyMuPDF
import os
import json

from pdf2image import convert_from_path
import pytesseract
from pytesseract import Output

from PIL import Image
import cv2
import numpy as np

def preprocess_image(pil_img):
    """Advanced preprocessing for OCR accuracy."""
    img = np.array(pil_img.convert('RGB')) # Always convert
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    # De-noise
    gray = cv2.fastNlMeansDenoising(gray, h=30)
    # Contrast enhancement
    gray = cv2.equalizeHist(gray)
    # Binarization (adaptive, robust for uneven lighting)
    bin_img = cv2.adaptiveThreshold(gray, 255,
                cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, 21, 15)
    # Optionally: deskewing can also be added here
    return Image.fromarray(bin_img)

def extract_outline(pdf_path):
    doc = fitz.open(pdf_path)
    text_blocks = []
    font_sizes = set()

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    line_text = ""
                    line_fonts = []
                    for span in line["spans"]:
                        line_text += span["text"]
                        line_fonts.append((span["size"], span["font"]))
                    if line_text.strip():
                        sizes = [fs[0] for fs in line_fonts]
                        avg_size = round(sum(sizes)/len(sizes), 2)
                        font_sizes.add(avg_size)
                        text_blocks.append({
                            "text": line_text.strip(),
                            "font_size": avg_size,
                            "bold": any("Bold" in f[1] for f in line_fonts),
                            "page": page_num + 1
                        })

    sorted_sizes = sorted(font_sizes, reverse=True)
    if not sorted_sizes:
        return extract_outline_ocr(pdf_path)  # Fallback to OCR

    title_size = sorted_sizes[0]
    h1_size = sorted_sizes[1] if len(sorted_sizes) > 1 else title_size
    h2_size = sorted_sizes[2] if len(sorted_sizes) > 2 else h1_size
    h3_size = sorted_sizes[3] if len(sorted_sizes) > 3 else h2_size

    # Get title: Largest font on first page
    title = None
    for blk in text_blocks:
        if blk["font_size"] == title_size and blk["page"] == 1:
            title = blk["text"]
            break
    if not title:
        title = os.path.splitext(os.path.basename(pdf_path))[0]

    outline = []
    for blk in text_blocks:
        if blk["font_size"] == h1_size and blk["bold"]:
            outline.append({"level": "H1", "text": blk["text"], "page": blk["page"]})
        elif blk["font_size"] == h2_size:
            outline.append({"level": "H2", "text": blk["text"], "page": blk["page"]})
        elif blk["font_size"] == h3_size:
            outline.append({"level": "H3", "text": blk["text"], "page": blk["page"]})

    return {
        "title": title,
        "outline": outline
    }

def extract_outline_ocr(pdf_path):
    try:
        images = convert_from_path(pdf_path, dpi=200)
    except Exception as e:
        return {
            "title": os.path.splitext(os.path.basename(pdf_path))[0],
            "outline": []
        }
    ocr_blocks = []
    for i, img in enumerate(images):
        pre_img = preprocess_image(img)
        # Get bounding box info for each word/line
        ocr_data = pytesseract.image_to_data(pre_img, output_type=Output.DICT)
        lines = []
        current_line_num = None
        line_text = ""
        line_bbox = None
        for i_word in range(len(ocr_data['text'])):
            text = ocr_data['text'][i_word].strip()
            if not text: continue
            line_num = ocr_data['line_num'][i_word]
            # Detect new line
            if current_line_num is None or line_num != current_line_num:
                if line_text:
                    lines.append((line_text, line_bbox))
                line_text = text
                line_bbox = (
                    ocr_data['left'][i_word],
                    ocr_data['top'][i_word],
                    ocr_data['width'][i_word],
                    ocr_data['height'][i_word]
                )
                current_line_num = line_num
            else:
                line_text += ' ' + text
                # Expand bbox as needed
                l, t, w, h = line_bbox
                nl = min(l, ocr_data['left'][i_word])
                nt = min(t, ocr_data['top'][i_word])
                nw = max(l+w, ocr_data['left'][i_word]+ocr_data['width'][i_word]) - nl
                nh = max(t+h, ocr_data['top'][i_word]+ocr_data['height'][i_word]) - nt
                line_bbox = (nl, nt, nw, nh)
        if line_text:
            lines.append((line_text, line_bbox))
        ocr_blocks.append({'lines': lines, 'page': i+1})

    # Header extraction heuristics
    outline = []
    title = None
    # Estimate typical text height for the page
    all_heights = []
    for block in ocr_blocks:
        for text, bbox in block['lines']:
            if bbox: all_heights.append(bbox[-1])
    common_height = np.percentile(all_heights, 60) if all_heights else 12

    for block in ocr_blocks:
        lines = block['lines']
        page = block['page']
        for idx, (line, bbox) in enumerate(lines):
            if not bbox: continue
            h = bbox[-1]
            clean = line.strip()
            if len(clean) < 3 or clean.isnumeric(): continue
            # Title: Largest, first lines on first page
            if (not title and page == 1 and idx < 3 and
                (h > common_height * 1.5 or clean.isupper()) and
                2 <= len(clean.split()) <= 15):
                title = clean
                continue
            # H1: Large, all caps, isolated
            if h > common_height * 1.3 and clean.isupper() and len(clean.split()) <= 12 and clean != title:
                outline.append({"level": "H1", "text": clean, "page": page})
            # H2: Medium-large, Title Case
            elif h > common_height*1.1 and clean.istitle() and len(clean.split()) <= 14 and clean != title:
                outline.append({"level": "H2", "text": clean, "page": page})
            # H3: Numbered or short
            elif ((clean[:1].isdigit() or clean.istitle()) and len(clean.split()) <= 14 and clean != title):
                outline.append({"level": "H3", "text": clean, "page": page})

    if not title:
        title = outline[0]["text"] if outline else os.path.splitext(os.path.basename(pdf_path))[0]

    # Deduplicate outline (same text/level/page)
    seen = set()
    deduped_outline = []
    for item in outline:
        key = (item['level'], item['text'], item['page'])
        if key not in seen:
            deduped_outline.append(item)
            seen.add(key)

    return {"title": title, "outline": deduped_outline}

def main():
    input_dir = os.path.join(os.getcwd(), 'input')
    output_dir = os.path.join(os.getcwd(), 'output')
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            inp_path = os.path.join(input_dir, filename)
            result = extract_outline(inp_path)
            out_name = os.path.splitext(filename)[0] + ".json"
            out_path = os.path.join(output_dir, out_name)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("Starting processing pdfs")
    main()
    print("completed processing pdfs")
