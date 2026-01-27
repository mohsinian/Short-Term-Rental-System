# Dockerfile for Pipeline Service (Local Development Only)
# This Dockerfile builds the pipeline service for data processing.
# NOT used for cloud deployment - only for local development.
# For production API deployment, use api/Dockerfile instead.

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install all dependencies (API + Pipeline)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . .

CMD ["python", "--version"]