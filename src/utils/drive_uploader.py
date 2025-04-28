"""
Google Drive Uploader for Startup Finder.

This module provides functionality to upload CSV files to Google Drive.
"""

import os
import logging
from typing import Optional
import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']


class GoogleDriveUploader:
    """
    Class for uploading files to Google Drive.
    """

    def __init__(self, credentials_path: str = 'credentials.json', token_path: str = 'token.json'):
        """
        Initialize the Google Drive uploader.

        Args:
            credentials_path: Path to the credentials.json file.
            token_path: Path to the token.json file.
        """
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive API.

        Returns:
            True if authentication was successful, False otherwise.
        """
        creds = None

        # The file token.json stores the user's access and refresh tokens
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(Path(self.token_path).read_text()), 
                    SCOPES
                )
            except Exception as e:
                logger.error(f"Error loading token: {e}")

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    logger.error(f"Error during authentication flow: {e}")
                    return False

            # Save the credentials for the next run
            try:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info(f"Saved authentication token to {self.token_path}")
            except Exception as e:
                logger.error(f"Error saving token: {e}")

        try:
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully authenticated with Google Drive")
            return True
        except Exception as e:
            logger.error(f"Error building Drive service: {e}")
            return False

    def upload_file(self, file_path: str, folder_id: Optional[str] = None) -> Optional[str]:
        """
        Upload a file to Google Drive.

        Args:
            file_path: Path to the file to upload.
            folder_id: ID of the folder to upload to. If None, uploads to root.

        Returns:
            File ID if successful, None otherwise.
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Authentication failed. Cannot upload file.")
                return None

        try:
            file_metadata = {
                'name': os.path.basename(file_path),
            }
            
            # If folder_id is provided, set the parent folder
            if folder_id:
                file_metadata['parents'] = [folder_id]

            media = MediaFileUpload(
                file_path,
                mimetype='text/csv',
                resumable=True
            )

            # Create the file in Google Drive
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink'
            ).execute()

            file_id = file.get('id')
            web_link = file.get('webViewLink')
            
            logger.info(f"File uploaded successfully. File ID: {file_id}")
            logger.info(f"Web view link: {web_link}")
            
            return file_id
        except HttpError as error:
            logger.error(f"An error occurred during upload: {error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            return None

    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
        """
        Create a folder in Google Drive.

        Args:
            folder_name: Name of the folder to create.
            parent_folder_id: ID of the parent folder. If None, creates in root.

        Returns:
            Folder ID if successful, None otherwise.
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Authentication failed. Cannot create folder.")
                return None

        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # If parent_folder_id is provided, set the parent folder
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]

            # Create the folder in Google Drive
            folder = self.service.files().create(
                body=file_metadata,
                fields='id'
            ).execute()

            folder_id = folder.get('id')
            logger.info(f"Folder created successfully. Folder ID: {folder_id}")
            
            return folder_id
        except HttpError as error:
            logger.error(f"An error occurred during folder creation: {error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during folder creation: {e}")
            return None

    def get_file_link(self, file_id: str) -> Optional[str]:
        """
        Get the web view link for a file.

        Args:
            file_id: ID of the file.

        Returns:
            Web view link if successful, None otherwise.
        """
        if not self.service:
            if not self.authenticate():
                logger.error("Authentication failed. Cannot get file link.")
                return None

        try:
            # Get the file metadata
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()

            web_link = file.get('webViewLink')
            return web_link
        except HttpError as error:
            logger.error(f"An error occurred while getting file link: {error}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while getting file link: {e}")
            return None


def upload_to_drive(file_path: str, credentials_path: str = 'credentials.json', 
                   folder_name: Optional[str] = None) -> Optional[str]:
    """
    Upload a file to Google Drive.

    Args:
        file_path: Path to the file to upload.
        credentials_path: Path to the credentials.json file.
        folder_name: Name of the folder to upload to. If None, uploads to root.

    Returns:
        Web view link if successful, None otherwise.
    """
    try:
        # Create the uploader
        uploader = GoogleDriveUploader(credentials_path=credentials_path)
        
        # Authenticate
        if not uploader.authenticate():
            logger.error("Failed to authenticate with Google Drive.")
            return None
        
        # Create folder if needed
        folder_id = None
        if folder_name:
            folder_id = uploader.create_folder(folder_name)
            if not folder_id:
                logger.warning(f"Failed to create folder '{folder_name}'. Uploading to root instead.")
        
        # Upload the file
        file_id = uploader.upload_file(file_path, folder_id)
        if not file_id:
            logger.error("Failed to upload file.")
            return None
        
        # Get the web view link
        web_link = uploader.get_file_link(file_id)
        if web_link:
            logger.info(f"File uploaded successfully. Web view link: {web_link}")
            return web_link
        else:
            logger.error("Failed to get web view link.")
            return None
    
    except Exception as e:
        logger.error(f"Error uploading to Google Drive: {e}")
        return None
