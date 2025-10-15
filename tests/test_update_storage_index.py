"""
Unit tests for update_storage_index.py
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from update_storage_index import (
    breadcrumb,
    generate_html,
    list_level,
    main,
    process_directory_recursively,
    write_index,
)


class TestUpdateStorageIndex(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.bucket_name = "test-bucket"
        self.prefix = "test-prefix"
        self.file_names = ["file1.mp4", "file2.mp4", "file3.mp4"]
        self.folder_names = ["subdir1/", "subdir2/"]

    def test_list_level_with_prefix(self):
        """Test list_level function with prefix."""
        # Mock bucket and blobs iterator
        mock_bucket = MagicMock()
        mock_blobs_iter = MagicMock()

        # Create mock blobs
        mock_blobs = []
        for name in self.file_names:
            mock_blob = MagicMock()
            mock_blob.name = f"{self.prefix}/{name}"
            mock_blobs.append(mock_blob)

        mock_blobs_iter.__iter__ = lambda x: iter(mock_blobs)
        mock_blobs_iter.prefixes = [
            f"{self.prefix}/{folder}" for folder in self.folder_names
        ]
        mock_bucket.list_blobs.return_value = mock_blobs_iter

        files, folders, normalized_prefix = list_level(mock_bucket, self.prefix)

        # Verify results
        expected_files = [(name, f"{self.prefix}/{name}") for name in self.file_names]
        expected_folders = [
            (folder, f"{self.prefix}/{folder}") for folder in self.folder_names
        ]

        self.assertEqual(files, expected_files)
        self.assertEqual(folders, expected_folders)
        self.assertEqual(normalized_prefix, f"{self.prefix}/")
        mock_bucket.list_blobs.assert_called_once_with(
            prefix=f"{self.prefix}/", delimiter="/"
        )

    def test_list_level_without_prefix(self):
        """Test list_level function without prefix."""
        # Mock bucket and blobs iterator
        mock_bucket = MagicMock()
        mock_blobs_iter = MagicMock()

        # Create mock blobs
        mock_blobs = []
        for name in self.file_names:
            mock_blob = MagicMock()
            mock_blob.name = name
            mock_blobs.append(mock_blob)

        mock_blobs_iter.__iter__ = lambda x: iter(mock_blobs)
        mock_blobs_iter.prefixes = self.folder_names
        mock_bucket.list_blobs.return_value = mock_blobs_iter

        files, folders, normalized_prefix = list_level(mock_bucket, "")

        # Verify results
        expected_files = [(name, name) for name in self.file_names]
        expected_folders = [(folder, folder) for folder in self.folder_names]

        self.assertEqual(files, expected_files)
        self.assertEqual(folders, expected_folders)
        self.assertEqual(normalized_prefix, "")
        mock_bucket.list_blobs.assert_called_once_with(prefix="", delimiter="/")

    def test_breadcrumb_with_prefix(self):
        """Test breadcrumb generation with prefix."""
        result = breadcrumb(self.bucket_name, self.prefix)
        expected = f'<a href="https://storage.googleapis.com/{self.bucket_name}/index.html">/{self.bucket_name}</a> / <a href="https://storage.googleapis.com/{self.bucket_name}/{self.prefix}/index.html">test-prefix</a> /'
        self.assertEqual(result, expected)

    def test_breadcrumb_without_prefix(self):
        """Test breadcrumb generation without prefix."""
        result = breadcrumb(self.bucket_name, "")
        expected = f'<a href="https://storage.googleapis.com/{self.bucket_name}/index.html">/{self.bucket_name}</a>'
        self.assertEqual(result, expected)

    def test_breadcrumb_with_nested_prefix(self):
        """Test breadcrumb generation with nested prefix."""
        nested_prefix = "level1/level2"
        result = breadcrumb(self.bucket_name, nested_prefix)
        self.assertIn("level1", result)
        self.assertIn("level2", result)
        self.assertIn("level1/level2/index.html", result)

    def test_generate_html_with_files_and_folders(self):
        """Test HTML generation with files and folders."""
        files = [("file1.mp4", "test-prefix/file1.mp4")]
        folders = [("subdir/", "test-prefix/subdir/")]

        html = generate_html(self.bucket_name, self.prefix, files, folders)

        # Check basic HTML structure
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn('<html lang="en">', html)
        self.assertIn(f"<title>{self.bucket_name}/{self.prefix}</title>", html)

        # Check content
        self.assertIn("file1.mp4", html)
        self.assertIn("subdir", html)
        self.assertIn("Folders", html)
        self.assertIn("Files", html)

        # Check links
        self.assertIn(
            f"https://storage.googleapis.com/{self.bucket_name}/test-prefix/file1.mp4",
            html,
        )
        self.assertIn(
            f"https://storage.googleapis.com/{self.bucket_name}/test-prefix/subdir/index.html",
            html,
        )

    def test_generate_html_without_files_or_folders(self):
        """Test HTML generation without files or folders."""
        html = generate_html(self.bucket_name, self.prefix, [], [])

        self.assertIn("No subfolders", html)
        self.assertIn("No files in this folder", html)

    def test_list_level_excludes_index_html(self):
        """Test that list_level excludes index.html files from the results."""
        # Mock bucket and blobs iterator
        mock_bucket = MagicMock()
        mock_blobs_iter = MagicMock()

        # Create mock blobs including index.html
        mock_blobs = []
        file_names_with_index = ["file1.mp4", "index.html", "file2.mp4"]
        for name in file_names_with_index:
            mock_blob = MagicMock()
            mock_blob.name = f"{self.prefix}/{name}"
            mock_blobs.append(mock_blob)

        mock_blobs_iter.__iter__ = lambda x: iter(mock_blobs)
        mock_blobs_iter.prefixes = []
        mock_bucket.list_blobs.return_value = mock_blobs_iter

        files, folders, normalized_prefix = list_level(mock_bucket, self.prefix)

        # Verify that index.html is excluded from files
        expected_files = [
            ("file1.mp4", f"{self.prefix}/file1.mp4"),
            ("file2.mp4", f"{self.prefix}/file2.mp4")
        ]
        self.assertEqual(files, expected_files)

        # Verify that index.html is not in the files list
        file_names = [name for name, _ in files]
        self.assertNotIn("index.html", file_names)

    def test_generate_html_with_index_html_in_files_list(self):
        """Test that generate_html still works correctly even if index.html is passed in files list.
        Note: In normal operation, list_level filters out index.html, but this tests the generate_html function directly."""
        # Include index.html in the files list to test that generate_html handles it
        files = [
            ("file1.mp4", "test-prefix/file1.mp4"),
            ("index.html", "test-prefix/index.html"),
            ("file2.mp4", "test-prefix/file2.mp4")
        ]
        folders = [("subdir/", "test-prefix/subdir/")]

        html = generate_html(self.bucket_name, self.prefix, files, folders)

        # Check that all files including index.html are included (since generate_html doesn't filter)
        self.assertIn("file1.mp4", html)
        self.assertIn("file2.mp4", html)
        self.assertIn("index.html", html)  # This will be included since generate_html doesn't filter

        # Verify the HTML structure is correct
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Files", html)

    def test_end_to_end_index_html_exclusion(self):
        """Test the complete flow to ensure index.html is excluded from final HTML."""
        # Mock bucket and blobs iterator
        mock_bucket = MagicMock()
        mock_blobs_iter = MagicMock()

        # Create mock blobs including index.html
        mock_blobs = []
        file_names_with_index = ["file1.mp4", "index.html", "file2.mp4"]
        for name in file_names_with_index:
            mock_blob = MagicMock()
            mock_blob.name = f"{self.prefix}/{name}"
            mock_blobs.append(mock_blob)

        mock_blobs_iter.__iter__ = lambda x: iter(mock_blobs)
        mock_blobs_iter.prefixes = []
        mock_bucket.list_blobs.return_value = mock_blobs_iter

        # Call list_level to get filtered files
        files, folders, normalized_prefix = list_level(mock_bucket, self.prefix)

        # Generate HTML with the filtered files
        html = generate_html(self.bucket_name, self.prefix, files, folders)

        # Verify that index.html is NOT in the final HTML as a file link
        # (it may appear in breadcrumbs, which is expected)
        # Check that there's no file link to index.html in the Files section
        self.assertNotIn('<li>📄 <a href="https://storage.googleapis.com/test-bucket/test-prefix/index.html">index.html</a></li>', html)
        # Also check that index.html doesn't appear as a file name in the Files section
        self.assertNotIn('>index.html</a>', html)

        # Verify that other files are still included
        self.assertIn("file1.mp4", html)
        self.assertIn("file2.mp4", html)

        # Verify the HTML structure is correct
        self.assertIn("<!DOCTYPE html>", html)
        self.assertIn("Files", html)

    @patch("update_storage_index.logger")
    def test_write_index(self, mock_logger):
        """Test writing index to bucket."""
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        html_content = "<html>test</html>"
        write_index(mock_bucket, self.prefix, html_content)

        mock_bucket.blob.assert_called_once_with(f"{self.prefix}index.html")
        mock_blob.upload_from_string.assert_called_once_with(
            html_content, content_type="text/html"
        )
        mock_logger.info.assert_called_once()

    @patch("update_storage_index.write_index")
    @patch("update_storage_index.generate_html")
    @patch("update_storage_index.list_level")
    @patch("update_storage_index.logger")
    def test_process_directory_recursively(
        self, mock_logger, mock_list_level, mock_generate_html, mock_write_index
    ):
        """Test recursive directory processing."""
        mock_bucket = MagicMock()

        # Mock list_level to return files and folders
        files = [("file1.mp4", "test-prefix/file1.mp4")]
        folders = [("subdir/", "test-prefix/subdir/")]
        mock_list_level.return_value = (files, folders, self.prefix)

        # Mock generate_html
        mock_generate_html.return_value = "<html>test</html>"

        # Mock recursive call to avoid infinite recursion
        with patch(
            "update_storage_index.process_directory_recursively"
        ) as mock_recursive:
            mock_recursive.side_effect = lambda bucket, bucket_name, prefix: None

            process_directory_recursively(mock_bucket, self.bucket_name, self.prefix)

            # Verify calls
            mock_list_level.assert_called_once_with(mock_bucket, self.prefix)
            mock_generate_html.assert_called_once_with(
                self.bucket_name, self.prefix, files, folders
            )
            mock_write_index.assert_called_once_with(
                mock_bucket, self.prefix, "<html>test</html>"
            )

    @patch("update_storage_index.storage.Client")
    @patch("update_storage_index.os.getenv")
    def test_main_with_missing_bucket_name(self, mock_getenv, mock_client):
        """Test main function with missing bucket name."""
        mock_getenv.side_effect = lambda x, default="": ""

        with self.assertRaises(ValueError) as context:
            main()
        self.assertIn("BUCKET_NAME is required", str(context.exception))

    @patch("update_storage_index.storage.Client")
    @patch("update_storage_index.os.getenv")
    def test_main_with_missing_prefix(self, mock_getenv, mock_client):
        """Test main function with missing prefix."""

        def mock_getenv_side_effect(key, default=""):
            if key == "BUCKET_NAME":
                return "test-bucket"
            elif key == "BUCKET_PREFIX":
                return None  # Simulate missing environment variable
            return default

        mock_getenv.side_effect = mock_getenv_side_effect

        # This should raise AttributeError because .strip() is called on None
        with self.assertRaises(AttributeError):
            main()

    @patch("update_storage_index.process_directory_recursively")
    @patch("update_storage_index.storage.Client")
    @patch("update_storage_index.os.getenv")
    def test_main_successful_execution(self, mock_getenv, mock_client, mock_process):
        """Test successful execution of main function."""
        # Mock environment variables
        mock_getenv.side_effect = lambda x, default="": {
            "BUCKET_NAME": self.bucket_name,
            "BUCKET_PREFIX": self.prefix,
        }.get(x, default)

        # Mock storage client
        mock_bucket = MagicMock()
        mock_client.return_value.bucket.return_value = mock_bucket

        # Run main
        main()

        # Verify calls
        mock_client.assert_called_once()
        mock_client.return_value.bucket.assert_called_once_with(self.bucket_name)
        mock_process.assert_called_once_with(mock_bucket, self.bucket_name, self.prefix)


if __name__ == "__main__":
    unittest.main()
