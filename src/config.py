"""
Configuration management for the secure payslip downloader.

Loads configuration from environment variables with sensible defaults.
Manages paths for credentials, schedules, downloads, and logs.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import logging


@dataclass
class Config:
    """
    Configuration for the secure payslip downloader.
    
    All paths are absolute and validated on initialization.
    Sensitive directories are created with secure permissions (0700).
    """
    
    # Gmail OAuth credentials path
    gmail_creds_path: Path
    
    # Base path for downloaded payslips
    download_base_path: Path
    
    # Timezone for scheduling (Israel timezone)
    timezone: str = "Asia/Jerusalem"
    
    # Logging configuration
    log_level: str = "INFO"
    log_dir: Path = None
    
    # Internal paths (computed from project structure)
    project_root: Path = None
    credentials_path: Path = None
    schedules_path: Path = None
    
    def __init__(
        self,
        gmail_creds_path: Optional[str] = None,
        download_base_path: Optional[str] = None,
        timezone: Optional[str] = None,
        log_level: Optional[str] = None
    ):
        """
        Initialize configuration from environment variables or defaults.
        
        Args:
            gmail_creds_path: Path to Gmail OAuth credentials.json
            download_base_path: Base directory for downloaded payslips
            timezone: Timezone for scheduling (default: Asia/Jerusalem)
            log_level: Logging level (default: INFO)
        """
        # Determine project root (parent of src directory)
        self.project_root = Path(__file__).parent.parent.resolve()
        
        # Gmail credentials path
        gmail_creds = gmail_creds_path or os.getenv(
            'GMAIL_CREDS_PATH',
            str(self.project_root / 'credentials' / 'credentials.json')
        )
        self.gmail_creds_path = Path(gmail_creds).resolve()
        
        # Download base path
        download_base = download_base_path or os.getenv(
            'DOWNLOAD_BASE_PATH',
            str(Path.home() / 'Documents' / 'Payslips')
        )
        self.download_base_path = Path(download_base).resolve()
        
        # Timezone
        self.timezone = timezone or os.getenv('TIMEZONE', 'Asia/Jerusalem')
        
        # Log level
        self.log_level = (log_level or os.getenv('LOG_LEVEL', 'INFO')).upper()
        
        # Internal paths
        self.credentials_path = self.project_root / 'credentials'
        self.schedules_path = self.project_root / 'schedules'
        self.log_dir = self.project_root / 'logs'
        
        # Validate configuration
        self._validate()
    
    def _validate(self):
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate log level
        valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
        if self.log_level not in valid_levels:
            raise ValueError(
                f"Invalid log level: {self.log_level}. "
                f"Must be one of: {', '.join(valid_levels)}"
            )
        
        # Validate timezone format (basic check)
        if '/' not in self.timezone:
            raise ValueError(
                f"Invalid timezone format: {self.timezone}. "
                f"Expected format: Continent/City (e.g., Asia/Jerusalem)"
            )
    
    def ensure_directories(self):
        """
        Create all required directories with appropriate permissions.
        
        Sensitive directories (credentials, schedules) get 0700 permissions.
        Other directories get 0755 permissions.
        """
        # Sensitive directories (only owner access)
        sensitive_dirs = [
            self.credentials_path,
            self.schedules_path,
            self.log_dir
        ]
        
        for dir_path in sensitive_dirs:
            dir_path.mkdir(mode=0o700, parents=True, exist_ok=True)
        
        # Download directory (normal permissions)
        self.download_base_path.mkdir(mode=0o755, parents=True, exist_ok=True)
    
    def get_download_path(self, year: int, filename: str) -> Path:
        """
        Get the full path for a downloaded payslip.
        
        Files are organized as: {base}/{year}/{filename}
        
        Args:
            year: Year for the payslip (e.g., 2025)
            filename: Sanitized filename for the payslip
            
        Returns:
            Full path where the payslip should be saved
            
        Examples:
            >>> config = Config()
            >>> config.get_download_path(2025, 'Payslip_November_2025.pdf')
            Path('/Users/username/Documents/Payslips/2025/Payslip_November_2025.pdf')
        """
        year_dir = self.download_base_path / str(year)
        year_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
        return year_dir / filename
    
    def get_schedules_file(self) -> Path:
        """Get path to schedules JSON file."""
        return self.schedules_path / 'tasks.json'
    
    def __repr__(self) -> str:
        """String representation of config (hides sensitive paths)."""
        return (
            f"Config(\n"
            f"  timezone={self.timezone},\n"
            f"  log_level={self.log_level},\n"
            f"  download_base={self.download_base_path},\n"
            f"  project_root={self.project_root}\n"
            f")"
        )


# Global config instance (initialized on first import)
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    
    Lazily initializes the config on first call.
    Subsequent calls return the same instance.
    
    Returns:
        Global Config instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
        _config_instance.ensure_directories()
    return _config_instance


def reload_config():
    """
    Reload configuration from environment variables.
    
    Useful for testing or when environment changes.
    """
    global _config_instance
    _config_instance = None
    return get_config()


# Convenience function for getting logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the configured log level.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    config = get_config()
    logger.setLevel(getattr(logging, config.log_level))
    return logger
