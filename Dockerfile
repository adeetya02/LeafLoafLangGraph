FROM python:3.11-slim

WORKDIR /app

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY config/ config/
COPY run_production.py .

# Copy demo files
COPY voice_demo_production.html src/static/
COPY voice_feedback_form.html src/static/
COPY voice_demo_deepgram.html src/static/

# Copy production env file if it exists (for local testing)
# In Cloud Run, env vars should come from deployment config
COPY .env.production.yaml* /app/

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=production
ENV GOOGLE_CLOUD_PROJECT=leafloafai

# Expose port (Cloud Run will override with PORT env var)
EXPOSE 8080

# Run the application
CMD ["python", "run_production.py"]