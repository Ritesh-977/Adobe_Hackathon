FROM python:3.10-slim

# System dependencies for pdfplumber/Poppler
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential gcc \
    libglib2.0-0 libsm6 libxrender1 libxext6 \
    poppler-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (specify exact versions for reproducibility)
RUN pip install --no-cache-dir pdfplumber scikit-learn numpy

# Copy your script and project into the image
COPY . .

# Default command: run your script (change script name if needed)
CMD ["python", "main.py"]
