FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure the app connects dynamically
ENV HOST=0.0.0.0
ENV PORT=8000

# Use array syntax so it handles signals properly
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
