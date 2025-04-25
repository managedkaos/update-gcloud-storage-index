# Use an official Python runtime as a parent image
FROM python:3.12-slim
ENV WORKDIR=/work
RUN mkdir /work

# Set the working directory in the container
WORKDIR ${WORKDIR}

# Install Google Cloud SDK and runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY update_storage_index.py /usr/local/bin/

# Create directory for credentials
RUN mkdir -p /root/.config

# Set environment variables
ENV GOOGLE_APPLICATION_CREDENTIALS=/root/.config/application_default_credentials.json

# Run the script when the container launches
ENTRYPOINT ["python", "/usr/local/bin/update_storage_index.py"]
