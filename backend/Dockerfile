FROM python:3.11-slim

# Create a non-root user required by Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Ensure the uploads directory exists and is writable by the user
RUN mkdir -p uploads && chmod 777 uploads

ENV HOST=0.0.0.0
ENV PORT=7860

# Use sh -c to chain migrations before starting the server
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 7860"]
