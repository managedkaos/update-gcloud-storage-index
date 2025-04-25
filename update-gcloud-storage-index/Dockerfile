# Use our base image that has Google Cloud SDK installed
FROM ghcr.io/managedkaos/update-gcloud-storage-index-base-image:latest

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script
COPY update_storage_index.py /usr/local/bin/

# Run the script when the container launches
ENTRYPOINT ["python", "/usr/local/bin/update_storage_index.py"]
