"""
Hierarchical index generator for a GCS bucket prefix.
Recursively creates index.html files for all directory levels.

ENV:
  BUCKET_NAME (required)
  BUCKET_PREFIX (required, e.g., "bucket-folder-name" or "" for the bucket root)
  PUBLIC_URL (optional; default https://storage.googleapis.com)
"""

import logging
import os
from urllib.parse import quote

from google.cloud import storage

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

DEFAULT_PUBLIC_URL = os.getenv("PUBLIC_URL", "https://storage.googleapis.com")
DEFAULT_BUCKET_NAME = ""
DEFAULT_PREFIX = ""


def list_level(bucket, prefix):
    """
    List immediate files and 'folders' under prefix using delimiter='/'
    Returns (files, folders) where:
      files   = [("name.ext", "full/object/path")]
      folders = [("subdir/", "full/object/prefix/")]
    """
    if prefix and not prefix.endswith("/"):
        prefix = prefix + "/"

    blobs_iter = bucket.list_blobs(prefix=prefix, delimiter="/")

    files = []
    for blob in blobs_iter:
        # Only immediate children (thanks to delimiter)
        name = blob.name[len(prefix) :] if prefix else blob.name
        if name and "/" not in name:
            files.append((name, blob.name))

    # 'prefixes' are subdirectory-like
    folders = []
    for sub_prefix in blobs_iter.prefixes:
        name = sub_prefix[len(prefix) :] if prefix else sub_prefix
        folders.append((name, sub_prefix))

    return files, folders, prefix


def breadcrumb(bucket_name, prefix):
    """
    Make breadcrumb HTML like: bucket / from-cover-to-code / ep1 /
    """
    parts = [] if not prefix else [p for p in prefix.strip("/").split("/") if p]
    crumbs = [
        f'<a href="{DEFAULT_PUBLIC_URL}/{bucket_name}/index.html">/{bucket_name}</a>'
    ]
    accum = ""
    for p in parts:
        accum = f"{accum}{p}/"
        url = f"{DEFAULT_PUBLIC_URL}/{bucket_name}/{quote(accum)}index.html"
        crumbs.append(f'<a href="{url}">{p}</a>')
    return " / ".join(crumbs) + (" /" if parts else "")


def generate_html(bucket_name, prefix, files, folders):
    title = f"{bucket_name}/{prefix}" if prefix else bucket_name
    bc = breadcrumb(bucket_name, prefix or "")

    html = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"<title>{title}</title>",
        # tiny inline styles for readability
        "<style>body{font-family:system-ui,Segoe UI,Arial,sans-serif;max-width:900px;margin:40px auto;padding:0 16px}"
        "h1{font-size:1.2rem} ul{line-height:1.7} .muted{color:#666;font-size:.9rem}</style>",
        "</head><body>",
        f"<h1>Index of <span class='muted'>{bc}</span></h1>",
        "<h2>Folders</h2>" if folders else "<p class='muted'>No subfolders</p>",
    ]

    if folders:
        html.append("<ul>")
        for name, full_prefix in sorted(folders, key=lambda x: x[0].lower()):
            href = f"{DEFAULT_PUBLIC_URL}/{bucket_name}/{quote(full_prefix)}index.html"
            html.append(f'<li>📁 <a href="{href}">{name}</a></li>')
        html.append("</ul>")

    html.append(
        "<h2>Files</h2>" if files else "<p class='muted'>No files in this folder</p>"
    )
    if files:
        html.append("<ul>")
        for name, full_path in sorted(files, key=lambda x: x[0].lower()):
            href = f"{DEFAULT_PUBLIC_URL}/{bucket_name}/{quote(full_path)}"
            html.append(f'<li>📄 <a href="{href}">{name}</a></li>')
        html.append("</ul>")

    html.append("</body></html>")
    return "\n".join(html)


def write_index(bucket, prefix, html):
    blob_path = f"{prefix}index.html" if prefix else "index.html"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(html, content_type="text/html")
    logger.info(f"Wrote index: {DEFAULT_PUBLIC_URL}/{bucket.name}/{blob_path}")


def process_directory_recursively(bucket, bucket_name, prefix=""):
    """
    Recursively process all directory levels starting from the given prefix.
    Creates index.html files for each directory level encountered.
    """
    logger.info(f"Processing directory: {prefix or 'root'}")

    # Get files and folders for current level
    files, folders, normalized_prefix = list_level(bucket, prefix)

    # Generate and write index for current level
    html = generate_html(bucket_name, normalized_prefix or "", files, folders)
    write_index(bucket, normalized_prefix or "", html)

    # Recursively process each subdirectory
    for folder_name, folder_prefix in folders:
        # Remove trailing slash from folder_prefix for recursive call
        clean_prefix = folder_prefix.rstrip("/")
        process_directory_recursively(bucket, bucket_name, clean_prefix)


def main():
    bucket_name = os.getenv("BUCKET_NAME", DEFAULT_BUCKET_NAME).strip()
    prefix = os.getenv("BUCKET_PREFIX", DEFAULT_PREFIX).strip()

    if not bucket_name:
        raise ValueError("BUCKET_NAME is required")
    if prefix is None:
        raise ValueError(
            "BUCKET_PREFIX is required (use '' for root, or e.g. 'bucket-folder-name')"
        )

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    logger.info(
        f"Starting recursive index generation for bucket: {bucket_name}, prefix: '{prefix}'"
    )
    process_directory_recursively(bucket, bucket_name, prefix)
    logger.info("Completed recursive index generation")


if __name__ == "__main__":
    main()
