FROM python:3.11-slim

# No network access at runtime — enforced via docker-compose network config
WORKDIR /sandbox

# Install deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run as non-root user for extra isolation
RUN useradd -m -u 1001 sandboxuser
USER sandboxuser

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
