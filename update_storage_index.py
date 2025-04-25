"""
This script lists the contents of a Google Cloud Storage (GCS)
bucket and generates a simple HTML page
"""

import logging
import os

from google.cloud import storage

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_PUBLIC_URL = os.getenv("PUBLIC_URL", "https://storage.googleapis.com")
DEFAULT_BUCKET_NAME = ""  # Default bucket
DEFAULT_PREFIX = ""  # Default directory within the bucket


def list_bucket_contents(bucket_name, prefix=None):
    """
    List the contents of a GCS bucket, optionally within a specific prefix (directory).
    """
    logger.info(f"Listing contents of bucket '{bucket_name}' with prefix '{prefix}'")
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    # If prefix is provided, ensure it ends with a slash
    if prefix and not prefix.endswith("/"):
        prefix = f"{prefix}/"

    blobs = bucket.list_blobs(prefix=prefix)

    # If we have a prefix, strip it from the blob names
    if prefix:
        file_names = [blob.name[len(prefix) :] for blob in blobs if blob.name != prefix]
    else:
        file_names = [blob.name for blob in blobs]

    logger.info(f"Found {len(file_names)} files in bucket")
    return file_names


def generate_html_page(bucket_name, file_names, prefix=None):
    """
    Generate a simple HTML page listing the contents of the bucket.
    """
    logger.info("Generating HTML page")
    title = f"{bucket_name}/{prefix}" if prefix else bucket_name

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
    </head>
    <body>
        <h1>Contents of {title}</h1>
        <ul>
    """

    for file_name in file_names:
        if prefix:
            public_url = f"{DEFAULT_PUBLIC_URL}/{bucket_name}/{prefix}/{file_name}"
        else:
            public_url = f"{DEFAULT_PUBLIC_URL}/{bucket_name}/{file_name}"
        html_content += f'<li><a href="{public_url}">{file_name}</a></li>\n'

    html_content += """
        </ul>
    </body>
    </html>
    """

    return html_content


def write_html_to_bucket(bucket_name, html_content, prefix=None):
    """
    Upload the generated HTML page back to the GCS bucket as index.html.
    """
    logger.info("Writing HTML page")
    client = storage.Client()
    bucket = client.get_bucket(bucket_name)

    # If prefix is provided, include it in the blob path
    blob_path = f"{prefix}/index.html" if prefix else "index.html"
    blob = bucket.blob(blob_path)

    # Write the HTML content as index.html to the bucket
    blob.upload_from_string(html_content, content_type="text/html")
    logger.info(f"index.html has been written to http://{bucket_name}/{blob_path}")


def main():
    """
    Main entry point of the script.
    """
    logger.info("Starting storage index update")

    # Get the bucket name and prefix from environment variables or use defaults
    bucket_name = os.getenv("BUCKET_NAME", DEFAULT_BUCKET_NAME)
    prefix = os.getenv("BUCKET_PREFIX", DEFAULT_PREFIX)

    if not bucket_name:
        logger.error("Bucket name is not set or is blank")
        raise ValueError("Bucket name is not set or is blank.")

    if not prefix:
        logger.error("Bucket prefix is not set or is blank")
        raise ValueError("Bucket prefix is not set or is blank.")

    logger.info(f"Using bucket: {bucket_name}, prefix: {prefix}")

    # List the contents of the bucket
    file_names = list_bucket_contents(bucket_name, prefix)

    # Generate the HTML page
    html_content = generate_html_page(bucket_name, file_names, prefix)

    # Write the HTML page back to the bucket as index.html
    write_html_to_bucket(bucket_name, html_content, prefix)

    logger.info("Storage index update completed successfully")


if __name__ == "__main__":
    main()
