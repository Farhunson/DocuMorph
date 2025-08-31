FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY . .

# Expose the port (must match Gunicorn bind)
EXPOSE 3000

# Start Flask with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:3000", "app:app"]
