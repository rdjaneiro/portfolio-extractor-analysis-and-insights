# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    procps \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install numpy first (as it's a common dependency that other packages might need)
RUN pip install --no-cache-dir numpy

# Copy requirements file first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for better security
ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# Copy the rest of the application
COPY . .

# Create directory for user files with appropriate permissions
RUN mkdir -p user_files && chown -R $USERNAME:$USERNAME /app

# Switch to non-root user
USER $USERNAME

# Expose the port for Streamlit
EXPOSE 8505

# Command to run when container starts
CMD ["streamlit", "run", "finTools_app.py"]

