# Use official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for non-interactive installs and production mode
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CORTEX_ENV=demo

# Create and set the working directory in the container
WORKDIR /code

# Copy dependency specifications and install them
COPY requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy all project directories and files into the container
COPY . /code

# Change directory to the backend so FastAPI can resolve modules correctly
WORKDIR /code/backend

# Hugging Face Spaces expects the container to expose and listen on port 7860
EXPOSE 7860

# CMD to start Uvicorn serving our FastAPI app
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "7860"]
