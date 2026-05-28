# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for non-interactive installs and production mode
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CORTEX_ENV=demo \
    OLLAMA_BASE_URL=http://127.0.0.1:11434 \
    USE_OLLAMA=true

# Create and set the working directory in the container
WORKDIR /code

# Copy dependency specifications and install them
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Install curl and bash so we can install and run Ollama in the container
RUN apt-get update && apt-get install -y curl bash && rm -rf /var/lib/apt/lists/*

# Copy all project directories and files into the container
COPY . /code

# Install the Ollama CLI at build time, but do not fail if the model pull is deferred
RUN if [ "${USE_OLLAMA}" = "true" ]; then \
      curl -fsSL https://ollama.com/install.sh | bash && \
      true; \
    fi

# Make the startup script executable
RUN chmod +x /code/start.sh

# Change directory to the backend so FastAPI can resolve modules correctly
WORKDIR /code/backend

# Hugging Face Spaces expects the container to expose and listen on port 7860
EXPOSE 7860

# Run Ollama and the FastAPI app together on startup.
CMD ["/code/start.sh"]
