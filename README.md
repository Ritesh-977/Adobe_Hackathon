# 📄  CHALLENGE 1B: PDF Outline Extractor

This tool extracts a **structured outline** from PDFs — including **Title**, **Headings (H1/H2/H3)** 

## 🧠 Approach

🔹 1. **Text-Based PDF Handling**
- Uses PyMuPDF (`fitz`) to extract structured text blocks.
- Collects font sizes and identifies the largest text as the **document title**.
- Classifies headings based on relative font sizes (`H1`, `H2`, `H3`), using the top 3 most frequent font sizes as thresholds.

🔹 2. **OCR Fallback for Image-Based PDFs**
- If no text is detected on a page, the page is rendered as an image.
- OCR is performed using Tesseract via `pytesseract`.
- OCR is **language-agnostic** with automatic script detection (`osd`).
- Includes **Right-to-Left (RTL)** language support for scripts like Arabic, Hebrew, etc.

 🔹 3. **Heading Detection Filters**
- Filters out noise such as:
  - Standalone numbers or table captions.
  - All-uppercase non-headings.
  - Lines too short or long.


## 📚 Libraries Used

`PyMuPDF` (`fitz`) ( PDF parsing and text extraction )
`pytesseract`   (OCR for image-based PDFs )     
`Pillow`        ( Image processing (used by `pytesseract`) )
`collections`   ( Font frequency analysis (`Counter`) )
`json`, `os`, `io` ( File handling and IO )

## 🛠 How to Build & Run

**Build**
docker build --no-cache --platform linux/amd64 -t myapp .

**RUN**
docker run --rm -v "${PWD}/input:/app/input" -v "${PWD}/output:/app/output" --network none myapp
