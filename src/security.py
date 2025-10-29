"""
Security utilities for the secure payslip downloader.

This module provides functions for:
- Filename sanitization to prevent path traversal attacks
- Secure file creation with proper permissions
- PDF validation
- Secure logging with credential redaction
"""

import os
import re
import stat
import logging
from pathlib import Path
from typing import Union


class SecurityError(Exception):
    """Raised when a security violation is detected."""
    pass


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.
    
    Security measures:
    - Remove path separators
    - Remove null bytes
    - Limit character set to alphanumeric, dash, underscore, dot
    - Prevent hidden files (no leading dots)
    - Limit length to 255 characters
    
    Args:
        filename: The filename to sanitize
        
    Returns:
        A safe filename with potentially dangerous characters removed/replaced
        
    Examples:
        >>> sanitize_filename('../../../etc/passwd')
        '_.._.._.._etc_passwd'
        >>> sanitize_filename('normal_file.pdf')
        'normal_file.pdf'
        >>> sanitize_filename('..hidden')
        '_hidden'
    """
    # Remove null bytes
    filename = filename.replace('\0', '')

    # Remove path separators (but keep dots for now)
    filename = filename.replace('/', '_').replace('\\', '_')

    # Prevent leading dots (hidden files on Unix)
    # Strip leading dots, and if the result is empty or doesn't start with underscore, prepend one
    had_leading_dots = filename.startswith('.')
    filename = filename.lstrip('.')

    if had_leading_dots and filename and not filename.startswith('_'):
        filename = '_' + filename
    elif had_leading_dots and not filename:
        filename = 'unnamed_file'

    # Keep only safe characters: alphanumeric, dash, underscore, dot
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    # Ensure not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename


def secure_join_path(base_dir: Path, *parts: str) -> Path:
    """
    Safely join paths, ensuring result is within base directory.
    
    Prevents path traversal attacks like:
    - /base/../../etc/passwd
    - /base/../../../sensitive_file
    
    Args:
        base_dir: The base directory that the result must be within
        *parts: Path components to join
        
    Returns:
        The safely joined path
        
    Raises:
        SecurityError: If the resulting path is outside the base directory
        
    Examples:
        >>> base = Path('/safe/base')
        >>> secure_join_path(base, 'subdir', 'file.txt')
        Path('/safe/base/subdir/file.txt')
        >>> secure_join_path(base, '../../../etc/passwd')  # Raises SecurityError
    """
    # Sanitize each part
    safe_parts = [sanitize_filename(part) for part in parts]
    
    # Join paths
    result_path = base_dir.joinpath(*safe_parts)
    
    # Resolve to absolute path
    result_path = result_path.resolve()
    base_dir = base_dir.resolve()
    
    # Verify result is within base directory
    try:
        result_path.relative_to(base_dir)
    except ValueError:
        raise SecurityError(
            f"Path traversal detected: {result_path} is outside {base_dir}"
        )
    
    return result_path


def create_secure_file(filepath: Path, content: bytes) -> None:
    """
    Create file with secure permissions (0600 - owner read/write only).
    
    Args:
        filepath: Path to the file to create
        content: Binary content to write to the file
        
    Raises:
        SecurityError: If secure permissions cannot be set
        
    Examples:
        >>> create_secure_file(Path('/tmp/secret.txt'), b'secret content')
    """
    # Create file with secure umask
    original_umask = os.umask(0o077)  # Mask out group/other permissions
    
    try:
        # Ensure parent directory exists
        filepath.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        
        # Write file
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Explicitly set permissions (redundant but safe)
        os.chmod(filepath, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        
    finally:
        # Restore original umask
        os.umask(original_umask)


def verify_secure_permissions(filepath: Path) -> bool:
    """
    Verify file has secure permissions (no group or other access).
    
    Args:
        filepath: Path to the file to check
        
    Returns:
        True if permissions are secure, False otherwise
        
    Examples:
        >>> verify_secure_permissions(Path('/tmp/secure_file.txt'))
        True
    """
    if not filepath.exists():
        return False
        
    file_stat = os.stat(filepath)
    mode = file_stat.st_mode
    
    # Check that group/other have no permissions
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        logging.warning(f"Insecure permissions on {filepath}: {oct(mode)}")
        return False
    
    return True


def validate_pdf(filepath: Path) -> bool:
    """
    Validate that a file is actually a PDF by checking magic bytes.
    
    PDF files start with "%PDF-" followed by version number.
    
    Args:
        filepath: Path to the file to validate
        
    Returns:
        True if file is a PDF, False otherwise
        
    Examples:
        >>> validate_pdf(Path('/tmp/document.pdf'))
        True
        >>> validate_pdf(Path('/tmp/not_a_pdf.txt'))
        False
    """
    if not filepath.exists():
        return False
    
    try:
        with open(filepath, 'rb') as f:
            # Read first 5 bytes
            header = f.read(5)
            # Check for PDF magic bytes
            return header == b'%PDF-'
    except Exception:
        return False


class SecureFormatter(logging.Formatter):
    """
    Logging formatter that redacts sensitive information.
    
    Automatically redacts patterns like:
    - tokens
    - passwords
    - API keys
    - client secrets
    - bearer tokens
    - Email addresses (partial redaction)
    """
    
    # Patterns for sensitive data (regex pattern, replacement)
    SENSITIVE_PATTERNS = [
        (r'token["\s:=]+["\']?([a-zA-Z0-9._-]+)["\']?', r'token="***REDACTED***"'),
        (r'password["\s:=]+["\']?([^\s"\']+)["\']?', r'password="***REDACTED***"'),
        (r'client_secret["\s:=]+["\']?([^\s"\']+)["\']?', r'client_secret="***REDACTED***"'),
        (r'api[_-]?key["\s:=]+["\']?([^\s"\']+)["\']?', r'api_key="***REDACTED***"'),
        (r'bearer\s+([a-zA-Z0-9._-]+)', r'bearer ***REDACTED***'),
        # Email addresses (partial redaction - keep domain)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', 
         r'\1[REDACTED]@\2'),
    ]
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with sensitive data redacted.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted log message with sensitive data redacted
        """
        # Format normally first
        message = super().format(record)
        
        # Apply redaction patterns
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        return message


def setup_secure_logging(log_dir: Path, log_level: str = 'INFO') -> None:
    """
    Configure logging with security measures.
    
    - Console handler with redaction
    - File handler with secure permissions
    - Credential redaction in both handlers
    
    Args:
        log_dir: Directory where log files will be stored
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Ensure log directory exists with secure permissions
    log_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    
    # Console handler with redaction
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(SecureFormatter(log_format))
    
    # File handler with secure permissions
    log_file = log_dir / 'app.log'
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(SecureFormatter(log_format))
    
    # Set secure permissions on log file
    if log_file.exists():
        os.chmod(log_file, 0o600)
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[console_handler, file_handler]
    )


def log_dict_safe(logger: logging.Logger, data: dict, level: int = logging.INFO) -> None:
    """
    Log dictionary with automatic credential masking.
    
    Masks keys that contain sensitive terms like:
    - token, password, secret, api_key, credentials
    - authorization, auth, private_key
    
    Args:
        logger: Logger instance to use
        data: Dictionary to log
        level: Logging level
        
    Examples:
        >>> logger = logging.getLogger(__name__)
        >>> log_dict_safe(logger, {'user': 'john@example.com', 'token': 'secret_123'})
        # Logs: Data: {'user': 'john@example.com', 'token': '***REDACTED***'}
    """
    sensitive_keys = {
        'token', 'password', 'secret', 'api_key', 'credentials',
        'authorization', 'auth', 'private_key', 'client_secret'
    }
    
    safe_data = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            safe_data[key] = "***REDACTED***"
        else:
            safe_data[key] = value
    
    logger.log(level, f"Data: {safe_data}")
