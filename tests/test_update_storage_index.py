"""
Unit tests for update_storage_index.py
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from update_storage_index import (
    generate_html_page,
    list_bucket_contents,
    write_html_to_bucket,
)


class TestUpdateStorageIndex(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.bucket_name = "test-bucket"
        self.prefix = "test-prefix"
        self.file_names = ["file1.mp4", "file2.mp4", "file3.mp4"]

    @patch("update_storage_index.storage.Client")
    def test_list_bucket_contents(self, mock_client):
        """Test listing bucket contents with and without prefix."""
        # Mock the bucket and blobs
        mock_bucket = MagicMock()
        mock_client.return_value.get_bucket.return_value = mock_bucket

        # Create mock blobs
        mock_blobs = []
        for name in self.file_names:
            mock_blob = MagicMock()
            mock_blob.name = name  # Don't include prefix in the mock blob names
            mock_blobs.append(mock_blob)

        # Configure the mock to return our blobs
        mock_bucket.list_blobs.return_value = mock_blobs

        # Test without prefix
        result = list_bucket_contents(self.bucket_name)
        self.assertEqual(result, self.file_names)
        mock_bucket.list_blobs.assert_called_once_with(prefix=None)

        # Test with prefix
        # Update mock blobs to include prefix
        for mock_blob in mock_blobs:
            mock_blob.name = f"{self.prefix}/{mock_blob.name}"
        result = list_bucket_contents(self.bucket_name, self.prefix)
        self.assertEqual(result, self.file_names)
        mock_bucket.list_blobs.assert_called_with(prefix=f"{self.prefix}/")

    def test_generate_html_page(self):
        """Test HTML page generation."""
        # Test without prefix
        html_content = generate_html_page(self.bucket_name, self.file_names)
        self.assertIn(self.bucket_name, html_content)
        for file_name in self.file_names:
            self.assertIn(file_name, html_content)
            self.assertIn(
                f"https://storage.googleapis.com/{self.bucket_name}/{file_name}",
                html_content,
            )

        # Test with prefix
        html_content = generate_html_page(
            self.bucket_name, self.file_names, self.prefix
        )
        self.assertIn(f"{self.bucket_name}/{self.prefix}", html_content)
        for file_name in self.file_names:
            self.assertIn(file_name, html_content)
            self.assertIn(
                f"https://storage.googleapis.com/{self.bucket_name}/{self.prefix}/{file_name}",
                html_content,
            )

    @patch("update_storage_index.storage.Client")
    def test_write_html_to_bucket(self, mock_client):
        """Test writing HTML to bucket."""
        # Mock the bucket and blob
        mock_bucket = MagicMock()
        mock_client.return_value.get_bucket.return_value = mock_bucket
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        # Test without prefix
        html_content = "<html>test</html>"
        write_html_to_bucket(self.bucket_name, html_content)
        mock_bucket.blob.assert_called_once_with("index.html")
        mock_blob.upload_from_string.assert_called_once_with(
            html_content, content_type="text/html"
        )

        # Test with prefix
        write_html_to_bucket(self.bucket_name, html_content, self.prefix)
        mock_bucket.blob.assert_called_with(f"{self.prefix}/index.html")

    @patch("update_storage_index.storage.Client")
    @patch("update_storage_index.os.getenv")
    def test_main_with_missing_environment_variables(self, mock_getenv, mock_client):
        """Test main function with missing environment variables."""
        from update_storage_index import main

        # Mock environment variables to return empty strings
        mock_getenv.side_effect = lambda x, default="": ""

        # Test that ValueError is raised when bucket name is missing
        with self.assertRaises(ValueError) as context:
            main()
        self.assertIn("Bucket name is not set or is blank", str(context.exception))

        # Test that ValueError is raised when prefix is missing
        mock_getenv.side_effect = lambda x, default="": (
            "test-bucket" if x == "BUCKET_NAME" else ""
        )
        with self.assertRaises(ValueError) as context:
            main()
        self.assertIn("Bucket prefix is not set or is blank", str(context.exception))

    @patch("update_storage_index.storage.Client")
    @patch("update_storage_index.os.getenv")
    def test_main_successful_execution(self, mock_getenv, mock_client):
        """Test successful execution of main function."""
        from update_storage_index import main

        # Mock environment variables
        mock_getenv.side_effect = lambda x, default="": {
            "BUCKET_NAME": self.bucket_name,
            "BUCKET_PREFIX": self.prefix,
        }.get(x, default)

        # Mock the storage client and its methods
        mock_bucket = MagicMock()
        mock_client.return_value.get_bucket.return_value = mock_bucket

        # Create mock blobs with proper names
        mock_blobs = []
        for name in self.file_names:
            mock_blob = MagicMock()
            mock_blob.name = f"{self.prefix}/{name}"
            mock_blobs.append(mock_blob)
        mock_bucket.list_blobs.return_value = mock_blobs

        # Run the main function
        main()

        # Verify the correct methods were called
        # Note: get_bucket is called twice - once for listing and once for writing
        self.assertEqual(mock_client.return_value.get_bucket.call_count, 2)
        mock_client.return_value.get_bucket.assert_any_call(self.bucket_name)
        mock_bucket.list_blobs.assert_called_once_with(prefix=f"{self.prefix}/")
        mock_bucket.blob.assert_called_once_with(f"{self.prefix}/index.html")


if __name__ == "__main__":
    unittest.main()
