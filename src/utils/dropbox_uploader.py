"""
Dropbox uploader for Startup Finder.

This module provides functionality to upload CSV files to Dropbox.
"""

import os
import logging
from typing import Optional, Tuple
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode

# Set up logging
logger = logging.getLogger(__name__)

class DropboxUploader:
    """
    A class to handle uploading files to Dropbox.
    """

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the DropboxUploader.

        Args:
            access_token: Dropbox API access token. If None, looks for
                         DROPBOX_ACCESS_TOKEN in environment variables.
        """
        self.access_token = access_token or os.environ.get('DROPBOX_ACCESS_TOKEN')
        self.dbx = None

    def authenticate(self) -> bool:
        """
        Authenticate with Dropbox API.

        Returns:
            bool: True if authentication was successful, False otherwise.
        """
        if not self.access_token:
            logger.error("No Dropbox access token provided")
            print("Error: No Dropbox access token provided. Please set DROPBOX_ACCESS_TOKEN environment variable.")
            return False

        try:
            self.dbx = dropbox.Dropbox(self.access_token)
            # Check that the access token is valid
            self.dbx.users_get_current_account()
            logger.info("Successfully authenticated with Dropbox")
            return True
        except AuthError as e:
            logger.error(f"Error authenticating with Dropbox: {e}")
            print(f"Error authenticating with Dropbox: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error connecting to Dropbox: {e}")
            print(f"Unexpected error connecting to Dropbox: {e}")
            return False

    def upload_file(self, file_path: str, dropbox_path: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """
        Upload a file to Dropbox.

        Args:
            file_path: Path to the file to upload.
            dropbox_path: Path in Dropbox where the file should be uploaded.
                         If None, uses the file name in the root folder.

        Returns:
            tuple: (path, shared_link) of the uploaded file, or None if upload failed.
        """
        if not self.dbx:
            if not self.authenticate():
                return None

        # If no Dropbox path is specified, use the file name in the root folder
        if not dropbox_path:
            dropbox_path = f"/{os.path.basename(file_path)}"
        
        # Make sure the Dropbox path starts with a slash
        if not dropbox_path.startswith('/'):
            dropbox_path = f"/{dropbox_path}"

        try:
            # Upload the file
            with open(file_path, 'rb') as f:
                logger.info(f"Uploading {file_path} to Dropbox path {dropbox_path}")
                self.dbx.files_upload(
                    f.read(),
                    dropbox_path,
                    mode=WriteMode('overwrite')
                )
            
            # Create a shared link
            shared_link_metadata = self.dbx.sharing_create_shared_link_with_settings(dropbox_path)
            shared_link = shared_link_metadata.url
            
            logger.info(f"File uploaded to Dropbox at {dropbox_path}")
            logger.info(f"Shared link: {shared_link}")
            
            return dropbox_path, shared_link
            
        except ApiError as e:
            logger.error(f"Error uploading file to Dropbox: {e}")
            print(f"Error uploading file to Dropbox: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading to Dropbox: {e}")
            print(f"Unexpected error uploading to Dropbox: {e}")
            return None

    def create_folder(self, folder_path: str) -> Optional[str]:
        """
        Create a folder in Dropbox.

        Args:
            folder_path: Path of the folder to create.

        Returns:
            str: Path of the created folder, or None if creation failed.
        """
        if not self.dbx:
            if not self.authenticate():
                return None

        # Make sure the folder path starts with a slash
        if not folder_path.startswith('/'):
            folder_path = f"/{folder_path}"

        try:
            self.dbx.files_create_folder_v2(folder_path)
            logger.info(f"Folder created in Dropbox at {folder_path}")
            return folder_path
            
        except ApiError as e:
            logger.error(f"Error creating folder in Dropbox: {e}")
            print(f"Error creating folder in Dropbox: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating folder in Dropbox: {e}")
            print(f"Unexpected error creating folder in Dropbox: {e}")
            return None
