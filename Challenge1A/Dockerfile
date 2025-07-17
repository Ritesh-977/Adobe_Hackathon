# Use a minimal, modern base image and specify platform
FROM --platform=linux/amd64 python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    gcc \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    libgl1 \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir pymupdf pdf2image pytesseract Pillow opencv-python

# Copy your python code and any other resources into the image
COPY . /app

# By default, run your main script (adjust if your script name differs)
ENTRYPOINT ["python", "main.py"]
