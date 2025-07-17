# 📄  CHALLENGE 1A: PDF Outline Extractor

This tool extracts a **structured outline** from PDFs — including **Title**, **Headings (H1/H2/H3)** 

## 🧠 Approach

🔹 1. **Text-Based PDF Handling**
- Uses PyMuPDF (`fitz`) to extract structured text blocks.
- Collects font sizes and identifies the largest text as the **document title**.
- Classifies headings based on relative font sizes (`H1`, `H2`, `H3`), using the top 3 most frequent font sizes as thresholds.

🔹 2. **OCR Fallback for Image-Based PDFs**
- If no text is found (scanned/image-based PDF), each page is converted to an image using pdf2image.
- Advanced image preprocessing (denoising, adaptive thresholding, contrast enhancement) is applied via OpenCV.
- Tesseract OCR extracts text and layout information.
- Heading detection uses bounding box sizes, position on the page, and text heuristics (ALL CAPS, Title Case, numbering patterns, etc).

 🔹 3. **Heading Detection Filters**
- Filters out noise such as:
  - Standalone numbers or table captions.
  - All-uppercase non-headings.
  - Lines too short or long.


## 📚 Libraries Used

- `PyMuPDF` (`fitz`) ( PDF parsing and text extraction )
- `pytesseract`   (OCR for image-based PDFs )     
- `Pillow`        ( Image processing (used by `pytesseract`) )
- `pdf2image`  (Convert PDF pages to images for OCR)
- `OpenCV`	  (Noise reduction, binarization, deskewing (image processing))
- `json`, `os` ( File handling )

## 🛠 How to Build & Run

**Build**
docker build --no-cache --platform linux/amd64 -t myapp .

**RUN**
docker run --rm -v "${PWD}/input:/app/input" -v "${PWD}/output:/app/output" --network none myapp
