# DevOps Guide for Empower Portfolio WebArchive Extractor

This document provides instructions for building, running, and managing the Docker container for the Empower Portfolio WebArchive Extractor application.

## Docker Container Setup

### Prerequisites

- Docker installed on your system
- Docker Compose installed on your system (optional, for using docker-compose.yml)

### Building the Docker Image

1. Navigate to the project root directory:

```bash
cd /path/to/empower-portfolio-extractor
```

2. Build the Docker image:

```bash
docker build -t empower-extractor .
```

### Running the Container

#### Using Docker Run

Run the container with the following command:

```bash
docker run -d \
  --name empower-extractor \
  -p 8505:8505 \
  -v $(pwd):/app \
  empower-extractor
```

#### Using Docker Compose

Alternatively, use Docker Compose for a more streamlined setup:

```bash
docker-compose up -d
```

The application will be accessible at http://localhost:8505

### Development Mode

For development purposes, you can run specific services without Docker:

```bash
# Run Streamlit app in development mode
python dev_run.py streamlit

# Run Dash app in development mode
python dev_run.py dash
```

## Container Management

### Viewing Logs

```bash
# View container logs
docker logs empower-extractor

# Follow logs
docker logs -f empower-extractor
```

### Managing the Container

```bash
# Stop the container
docker stop empower-extractor

# Start a stopped container
docker start empower-extractor

# Restart the container
docker restart empower-extractor

# Remove the container
docker rm empower-extractor
```

### Updating the Application

1. Pull the latest code:

```bash
git pull
```

2. Rebuild the Docker image:

```bash
docker build -t empower-extractor .
```

3. Stop and remove the existing container:

```bash
docker stop empower-extractor
docker rm empower-extractor
```

4. Run a new container with the updated image:

```bash
docker run -d \
  --name empower-extractor \
  -p 8505:8505 \
  -v $(pwd):/app \
  empower-extractor
```

Or with Docker Compose:

```bash
docker-compose down
docker-compose up -d
```

## Environment Variables

The application supports the following environment variables:

- `PYTHONUNBUFFERED`: Set to 1 to ensure Python output is sent straight to the terminal (useful for debugging)

You can add more environment variables in the docker-compose.yml file or pass them with the `-e` flag when using `docker run`.

## Volume Mapping

The Docker setup maps your local project directory to `/app` inside the container, allowing you to:

- Make changes to code without rebuilding the container
- Access files processed by the application directly from your local filesystem

## Troubleshooting

### Container fails to start

Check the logs for errors:

```bash
docker logs empower-extractor
```

### Application is inaccessible

Verify the container is running:

```bash
docker ps
```

Check if the port mapping is correct:

```bash
docker port empower-extractor
```

### Permission issues with mounted volumes

Ensure the container has appropriate permissions to access the mounted directory:

```bash
chmod -R 755 /path/to/empower-portfolio-extractor
```