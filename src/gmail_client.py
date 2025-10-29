"""
Gmail API client for secure payslip downloading.

Handles OAuth authentication, email searching, and attachment downloading
with proper security measures and rate limiting.
"""

import base64
import time
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from functools import wraps

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_config, get_logger
from security import sanitize_filename, create_secure_file, validate_pdf

logger = get_logger(__name__)

# Gmail API scopes (read-only access)
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class GmailAuthError(Exception):
    """Raised when Gmail authentication fails."""
    pass


class GmailAPIError(Exception):
    """Raised when Gmail API operations fail."""
    pass


def rate_limited(max_per_second: float = 5.0):
    """
    Decorator to rate limit Gmail API calls.
    
    Args:
        max_per_second: Maximum calls per second (default: 5 for safety)
    """
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator


def handle_gmail_errors(func):
    """
    Decorator to handle Gmail API errors with exponential backoff.
    
    Automatically retries on rate limits and server errors.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    # Rate limit or server error - retry with backoff
                    wait_time = (2 ** attempt) + (time.time() % 1)  # Add jitter
                    logger.warning(
                        f"API error {e.resp.status}, "
                        f"retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    # Other error - don't retry
                    logger.error(f"Gmail API error: {e}")
                    raise GmailAPIError(f"Gmail API error: {e.resp.status}") from e
        
        raise GmailAPIError(f"Max retries ({max_retries}) exceeded")
    return wrapper


class GmailClient:
    """
    Gmail API client with OAuth authentication and rate limiting.
    
    Provides methods for searching emails and downloading attachments
    with proper security and error handling.
    """
    
    def __init__(self, credentials_path: Optional[Path] = None):
        """
        Initialize Gmail client.
        
        Args:
            credentials_path: Path to credentials.json (optional, uses config default)
        """
        self.config = get_config()
        self.credentials_path = credentials_path or self.config.gmail_creds_path
        self.token_path = self.credentials_path.parent / 'token.pickle'
        self._service = None
    
    def authenticate(self) -> Credentials:
        """
        Authenticate with Gmail using OAuth 2.0.
        
        - Loads existing token if available
        - Refreshes token if expired
        - Runs OAuth flow if no valid token
        
        Returns:
            Valid Google OAuth credentials
            
        Raises:
            GmailAuthError: If authentication fails
        """
        creds = None
        
        # Load existing token
        if self.token_path.exists():
            try:
                with open(self.token_path, 'rb') as token:
                    creds = pickle.load(token)
                logger.info("Loaded existing OAuth token")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                creds = None
        
        # Refresh or create new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing expired OAuth token")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    raise GmailAuthError("Failed to refresh OAuth token") from e
            else:
                # First-time OAuth flow
                if not self.credentials_path.exists():
                    raise GmailAuthError(
                        f"credentials.json not found at {self.credentials_path}. "
                        "Please download from Google Cloud Console."
                    )
                
                try:
                    logger.info("Starting OAuth flow")
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(self.credentials_path), SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("OAuth flow completed successfully")
                except Exception as e:
                    logger.error(f"OAuth flow failed: {e}")
                    raise GmailAuthError("OAuth authentication failed") from e
            
            # Save credentials for next run
            try:
                create_secure_file(self.token_path, pickle.dumps(creds))
                logger.info(f"Saved OAuth token to {self.token_path}")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")
        
        return creds
    
    def get_service(self):
        """
        Get Gmail API service, authenticating if necessary.
        
        Returns:
            Gmail API service object
        """
        if self._service is None:
            creds = self.authenticate()
            self._service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail API service initialized")
        return self._service
    
    def _build_search_query(
        self,
        sender: str,
        days_back: int,
        subject_keywords: Optional[str] = None
    ) -> str:
        """
        Build Gmail search query string.
        
        Args:
            sender: Email address to search from
            days_back: Number of days to search back
            subject_keywords: Optional keywords to match in subject
            
        Returns:
            Gmail search query string
        """
        # Calculate date range
        after_date = datetime.now() - timedelta(days=days_back)
        after_str = after_date.strftime('%Y/%m/%d')
        
        # Build query
        query_parts = [
            f'from:{sender}',
            'has:attachment',
            f'after:{after_str}',
            'filename:pdf'  # Only PDF attachments
        ]
        
        if subject_keywords:
            query_parts.append(f'subject:{subject_keywords}')
        
        query = ' '.join(query_parts)
        logger.debug(f"Built search query: {query}")
        return query
    
    @rate_limited(max_per_second=5.0)
    @handle_gmail_errors
    def search_emails(
        self,
        sender_email: str,
        subject_keywords: Optional[str] = None,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Search for emails with PDF attachments from specific sender.
        
        Args:
            sender_email: Email address to search from
            subject_keywords: Optional keywords to match in subject
            days_back: Number of days to search back (default: 30)
            
        Returns:
            List of email dictionaries with metadata
            
        Raises:
            GmailAPIError: If search fails
        """
        service = self.get_service()
        query = self._build_search_query(sender_email, days_back, subject_keywords)
        
        logger.info(f"Searching emails from {sender_email} (last {days_back} days)")
        
        try:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            
            # Handle pagination
            while 'nextPageToken' in results:
                page_token = results['nextPageToken']
                results = service.users().messages().list(
                    userId='me',
                    q=query,
                    maxResults=100,
                    pageToken=page_token
                ).execute()
                messages.extend(results.get('messages', []))
            
            logger.info(f"Found {len(messages)} matching emails")
            
            # Get detailed info for each message
            detailed_messages = []
            for msg in messages:
                try:
                    details = self._get_email_details(msg['id'])
                    if details:
                        detailed_messages.append(details)
                except Exception as e:
                    logger.warning(f"Failed to get details for message {msg['id']}: {e}")
            
            return detailed_messages
            
        except Exception as e:
            logger.error(f"Email search failed: {e}")
            raise GmailAPIError(f"Failed to search emails") from e
    
    @rate_limited(max_per_second=5.0)
    @handle_gmail_errors
    def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an email.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary with email details or None if no PDF attachments
        """
        service = self.get_service()
        
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        # Extract headers
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Find PDF attachments
        attachments = []
        for part in message['payload'].get('parts', []):
            filename = part.get('filename', '')
            if filename and filename.lower().endswith('.pdf'):
                attachments.append({
                    'filename': filename,
                    'size': part['body'].get('size', 0),
                    'attachment_id': part['body'].get('attachmentId')
                })
        
        if not attachments:
            return None
        
        # Parse date
        date_str = headers.get('Date', '')
        try:
            # Simple date parsing (Gmail returns RFC 2822 format)
            date = datetime.strptime(date_str.split(',')[1].strip()[:20], '%d %b %Y %H:%M:%S')
        except:
            date = datetime.now()
        
        return {
            'id': message_id,
            'sender': headers.get('From', 'Unknown'),
            'subject': headers.get('Subject', 'No Subject'),
            'date': date.isoformat(),
            'attachments': attachments
        }
    
    def _sanitize_attachment_name(self, filename: str) -> str:
        """
        Sanitize attachment filename and validate PDF extension.
        
        Args:
            filename: Original attachment filename
            
        Returns:
            Sanitized filename
            
        Raises:
            ValueError: If filename is not a PDF
        """
        if not filename.lower().endswith('.pdf'):
            raise ValueError(f"Only PDF files are supported, got: {filename}")
        
        return sanitize_filename(filename)
    
    @rate_limited(max_per_second=3.0)  # Lower rate for downloads
    @handle_gmail_errors
    def download_attachment(
        self,
        message_id: str,
        attachment_id: str,
        output_path: Path
    ) -> Path:
        """
        Download email attachment to specified path.
        
        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID within message
            output_path: Path where file should be saved
            
        Returns:
            Path to downloaded file
            
        Raises:
            GmailAPIError: If download fails
            ValueError: If file is not a valid PDF
        """
        service = self.get_service()
        
        logger.info(f"Downloading attachment from message {message_id}")
        
        try:
            attachment = service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()
            
            # Decode attachment data
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            # Create file with secure permissions
            create_secure_file(output_path, file_data)
            
            # Validate it's actually a PDF
            if not validate_pdf(output_path):
                output_path.unlink()  # Delete invalid file
                raise ValueError(f"Downloaded file is not a valid PDF")
            
            logger.info(f"Successfully downloaded attachment to {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Attachment download failed: {e}")
            if output_path.exists():
                output_path.unlink()  # Clean up partial download
            raise GmailAPIError(f"Failed to download attachment") from e
    
    def _validate_pdf_attachment(self, filename: str):
        """Validate that attachment filename ends with .pdf"""
        if not filename.lower().endswith('.pdf'):
            raise ValueError(f"Only PDF files are supported: {filename}")
