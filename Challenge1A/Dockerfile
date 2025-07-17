FROM python:3.11-slim

ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    curl \
    poppler-utils \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Download language files to the correct location
RUN mkdir -p $TESSDATA_PREFIX && \
    cd $TESSDATA_PREFIX && \
    curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata && \
    curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/hin.traineddata && \
    curl -LO https://github.com/tesseract-ocr/tessdata/raw/main/ara.traineddata

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir pymupdf pytesseract pillow

COPY . .

# Optional: explicitly tell pytesseract where the binary is
ENV TESSERACT_CMD=/usr/bin/tesseract

CMD ["python", "main.py"]
