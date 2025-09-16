#All these instructions will be used to build a docker image and run this image on a container

# Use official Python image
FROM python:3.10-slim

# Set environment variables 0 means off 1 means on
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set workdir (a working directory inside the container will be created with name app)
WORKDIR /app

# Install OS dependencies and update the container system
RUN apt-get update && apt-get install -y build-essential poppler-utils && rm -rf /var/lib/apt/lists/*

# Copy requirements file to the working directory (. means current directory)
COPY requirements.txt .

COPY .env .

# Copy all project files to the working directory
COPY . .

# Install dependencies on the working directory in container
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run FastAPI with uvicorn on container start
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"]

# # Replace last CMD in prod
# CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]