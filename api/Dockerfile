# Dockerfile for FastAPI Backend (Production Deployment)
# This Dockerfile builds the production-ready API service.
# Used for cloud deployment - optimized for production use.
# For local pipeline development, use the root Dockerfile instead.

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install API-specific dependencies only (lighter, faster builds)
COPY api/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy API source code (only what's needed for the API)
COPY api/ ./api/
COPY src/ ./src/

# Expose port for FastAPI
EXPOSE 8000

# Run FastAPI with uvicorn (production mode - no reload)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
