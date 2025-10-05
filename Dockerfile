# Use Azure Functions Python base image with Python 3.11
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Install FFmpeg and other system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /home/site/wwwroot

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY function_app.py .
COPY processing/ ./processing/
COPY integrations/ ./integrations/
COPY config/ ./config/
COPY host.json ./

# Embed build metadata for version verification
ARG BUILD_TIME
ARG COMMIT_SHA
RUN echo ${BUILD_TIME:-unknown} > BUILD_TIME
RUN echo ${COMMIT_SHA:-unknown} > COMMIT_SHA

# CRITICAL: Prevent Python bytecode caching issues
# This ensures fresh imports on every container start
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    PYTHONPATH=/home/site/wwwroot

# Expose port
EXPOSE 80
