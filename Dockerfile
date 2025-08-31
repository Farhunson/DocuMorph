FROM python:3.10-slim

WORKDIR /app

# Install system dependencies needed by OpenCV (cv2) and pdf2docx
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose port
EXPOSE 3000

# Run with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
