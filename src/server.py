"""
FastMCP Server for Secure Payslip Downloader

This MCP server provides 5 tools for automated payslip management:
1. search_payslip_email - Search for payslip emails
2. download_payslip - Download a specific payslip attachment
3. create_monthly_schedule - Create automated monthly download
4. list_schedules - View all scheduled downloads
5. delete_schedule - Remove a scheduled download

Usage:
    mcp run src/server.py
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from fastmcp import FastMCP

# Import our modules
from gmail_client import GmailClient, GmailAPIError, GmailAuthError
from scheduler import ScheduleManager, Schedule, ValidationError, ScheduleError
from config import get_config, get_logger

# Initialize FastMCP server
mcp = FastMCP("secure-payslip-downloader")

# Initialize logger
logger = get_logger(__name__)

# Global instances (initialized on first use)
_gmail_client: Optional[GmailClient] = None
_schedule_manager: Optional[ScheduleManager] = None
_config = None


def get_gmail_client() -> GmailClient:
    """Get or create Gmail client instance."""
    global _gmail_client
    if _gmail_client is None:
        _gmail_client = GmailClient()
        logger.info("Gmail client initialized")
    return _gmail_client


def get_schedule_manager() -> ScheduleManager:
    """Get or create schedule manager instance."""
    global _schedule_manager
    if _schedule_manager is None:
        _schedule_manager = ScheduleManager()
        logger.info("Schedule manager initialized")
    return _schedule_manager


def get_app_config():
    """Get or create config instance."""
    global _config
    if _config is None:
        _config = get_config()
        logger.info("Configuration loaded")
    return _config


@mcp.tool()
def search_payslip_email(
    sender_email: str,
    subject_keywords: Optional[str] = None,
    days_back: int = 30
) -> Dict[str, Any]:
    """
    Search for payslip emails from a specific sender.

    This tool searches your Gmail inbox for emails with PDF attachments
    from the specified sender. Use this to find payslips before downloading.

    Args:
        sender_email: Email address to search from (e.g., "payroll@company.com")
        subject_keywords: Optional keywords to match in subject line (e.g., "payslip")
        days_back: Number of days to search back (default: 30)

    Returns:
        Dictionary containing:
        - emails: List of matching emails with metadata
        - count: Number of emails found

    Example:
        search_payslip_email(
            sender_email="payroll@company.com",
            subject_keywords="payslip",
            days_back=30
        )

    Raises:
        Error if Gmail authentication fails or API error occurs
    """
    try:
        logger.info(f"Searching emails from {sender_email}")

        # Get Gmail client
        client = get_gmail_client()

        # Verify authentication
        try:
            client.get_service()
        except GmailAuthError:
            return {
                "error": "Gmail authentication required. Please run: uv run python scripts/oauth_setup.py",
                "authenticated": False
            }

        # Search emails
        emails = client.search_emails(
            sender_email=sender_email,
            subject_keywords=subject_keywords,
            days_back=days_back
        )

        logger.info(f"Found {len(emails)} matching emails")

        return {
            "success": True,
            "count": len(emails),
            "emails": emails,
            "search_params": {
                "sender_email": sender_email,
                "subject_keywords": subject_keywords,
                "days_back": days_back
            }
        }

    except GmailAPIError as e:
        logger.error(f"Gmail API error: {e}")
        return {
            "success": False,
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Search failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }


@mcp.tool()
def download_payslip(
    message_id: str,
    attachment_id: str,
    filename: str
) -> Dict[str, Any]:
    """
    Download a specific payslip PDF attachment.

    Use this tool after searching for emails to download a specific
    PDF attachment. The file is saved to ~/Documents/Payslips/YYYY/filename
    with secure permissions.

    Args:
        message_id: Gmail message ID (from search results)
        attachment_id: Attachment ID within the message (from search results)
        filename: Original filename of the attachment

    Returns:
        Dictionary containing:
        - success: Whether download succeeded
        - file_path: Where the file was saved
        - size: File size in bytes

    Example:
        download_payslip(
            message_id="18f3a4b5c6d7e8f9",
            attachment_id="ANGjdJ8...",
            filename="Payslip_November_2025.pdf"
        )

    Raises:
        Error if download fails or file is not a valid PDF
    """
    try:
        logger.info(f"Downloading attachment: {filename}")

        # Get Gmail client and config
        client = get_gmail_client()
        config = get_app_config()

        # Verify authentication
        try:
            client.get_service()
        except GmailAuthError:
            return {
                "error": "Gmail authentication required. Please run: uv run python scripts/oauth_setup.py",
                "authenticated": False
            }

        # Determine year for directory organization (use current year)
        year = datetime.now().year

        # Get output path
        output_path = config.get_download_path(year, filename)

        # Check if file already exists
        if output_path.exists():
            logger.info(f"File already exists: {output_path}")
            return {
                "success": True,
                "already_exists": True,
                "file_path": str(output_path),
                "size": output_path.stat().st_size
            }

        # Download attachment
        downloaded_path = client.download_attachment(
            message_id=message_id,
            attachment_id=attachment_id,
            output_path=output_path
        )

        file_size = downloaded_path.stat().st_size
        logger.info(f"Downloaded {filename} ({file_size} bytes) to {downloaded_path}")

        return {
            "success": True,
            "file_path": str(downloaded_path),
            "size": file_size,
            "already_exists": False
        }

    except ValueError as e:
        # PDF validation failed
        logger.error(f"Invalid PDF: {e}")
        return {
            "success": False,
            "error": f"File is not a valid PDF: {str(e)}"
        }
    except GmailAPIError as e:
        logger.error(f"Download failed: {e}")
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Download failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Download failed: {str(e)}"
        }


@mcp.tool()
def create_monthly_schedule(
    sender_email: str,
    day_of_month: int,
    hour: int = 9,
    minute: int = 0,
    subject_keywords: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a monthly automated payslip download schedule.

    This creates a scheduled task that runs automatically every month
    via system cron. The schedule searches for and downloads payslips
    from the specified sender.

    Args:
        sender_email: Email address to download from (e.g., "payroll@company.com")
        day_of_month: Day of month to run (1-31, typically 11 for payslips)
        hour: Hour to run (0-23, default: 9 for 9 AM)
        minute: Minute to run (0-59, default: 0)
        subject_keywords: Optional keywords to match in subject (e.g., "payslip")
        description: Human-readable description of the schedule

    Returns:
        Dictionary containing:
        - success: Whether schedule was created
        - schedule_id: Unique ID for the schedule
        - schedule: Cron schedule string
        - cron_command: Command to add to crontab

    Example:
        create_monthly_schedule(
            sender_email="payroll@company.com",
            day_of_month=11,
            hour=9,
            minute=0,
            subject_keywords="payslip",
            description="Monthly payslip from Company Ltd"
        )

    Note:
        After creating a schedule, you need to set up the cron job once:
        1. Copy the cron_command from the response
        2. Run: crontab -e
        3. Add the command to your crontab
        4. Save and exit
    """
    try:
        logger.info(f"Creating monthly schedule for {sender_email}")

        # Validate inputs
        if not (1 <= day_of_month <= 31):
            return {
                "success": False,
                "error": f"day_of_month must be 1-31, got: {day_of_month}"
            }

        if not (0 <= hour <= 23):
            return {
                "success": False,
                "error": f"hour must be 0-23, got: {hour}"
            }

        if not (0 <= minute <= 59):
            return {
                "success": False,
                "error": f"minute must be 0-59, got: {minute}"
            }

        # Build cron schedule
        cron_schedule = f"{minute} {hour} {day_of_month} * *"

        # Get schedule manager
        manager = get_schedule_manager()
        config = get_app_config()

        # Create schedule
        schedule_id = manager.create_schedule(
            sender_email=sender_email,
            schedule=cron_schedule,
            subject_keywords=subject_keywords,
            description=description or f"Monthly payslip from {sender_email}",
            enabled=True
        )

        # Build cron command
        project_root = config.project_root
        cron_command = (
            f"{minute} {hour} {day_of_month} * * "
            f"cd {project_root} && "
            f"uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1"
        )

        logger.info(f"Created schedule {schedule_id}: {cron_schedule}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "schedule": cron_schedule,
            "schedule_readable": f"Every month on day {day_of_month} at {hour:02d}:{minute:02d}",
            "sender_email": sender_email,
            "subject_keywords": subject_keywords,
            "description": description,
            "cron_command": cron_command,
            "setup_instructions": [
                "1. Run: crontab -e",
                "2. Add the cron_command above to your crontab",
                "3. Save and exit",
                "4. Verify with: crontab -l"
            ]
        }

    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return {
            "success": False,
            "error": f"Invalid parameters: {str(e)}"
        }
    except ScheduleError as e:
        logger.error(f"Schedule creation failed: {e}")
        return {
            "success": False,
            "error": f"Failed to create schedule: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Schedule creation failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to create schedule: {str(e)}"
        }


@mcp.tool()
def list_schedules(enabled_only: bool = False) -> Dict[str, Any]:
    """
    List all scheduled payslip downloads.

    Shows all configured schedules, including their status, sender,
    schedule, and last run time.

    Args:
        enabled_only: If True, only show enabled schedules (default: False)

    Returns:
        Dictionary containing:
        - success: Whether operation succeeded
        - count: Number of schedules
        - schedules: List of schedule details

    Example:
        list_schedules(enabled_only=True)
    """
    try:
        logger.info(f"Listing schedules (enabled_only={enabled_only})")

        # Get schedule manager
        manager = get_schedule_manager()

        # Get schedules
        schedules = manager.list_schedules(enabled_only=enabled_only)

        # Get statistics
        stats = manager.count_schedules()

        # Format schedules for output
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                "schedule_id": schedule.schedule_id,
                "sender_email": schedule.sender_email,
                "subject_keywords": schedule.subject_keywords,
                "schedule": schedule.schedule,
                "enabled": schedule.enabled,
                "description": schedule.description,
                "created_at": schedule.created_at,
                "last_run": schedule.last_run
            })

        logger.info(f"Found {len(schedules)} schedules")

        return {
            "success": True,
            "count": len(schedules),
            "schedules": schedule_list,
            "statistics": stats
        }

    except ScheduleError as e:
        logger.error(f"Failed to list schedules: {e}")
        return {
            "success": False,
            "error": f"Failed to list schedules: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Failed to list schedules: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to list schedules: {str(e)}"
        }


@mcp.tool()
def delete_schedule(schedule_id: str) -> Dict[str, Any]:
    """
    Delete a scheduled payslip download.

    Removes a schedule from the system. The cron job will skip this
    schedule on future runs.

    Args:
        schedule_id: Schedule ID to delete (from list_schedules)

    Returns:
        Dictionary containing:
        - success: Whether deletion succeeded
        - schedule_id: ID of deleted schedule

    Example:
        delete_schedule(schedule_id="abc123...")

    Note:
        This only removes the schedule from the JSON file. If you've
        set up a cron job, it will continue to run but will skip
        deleted schedules.
    """
    try:
        logger.info(f"Deleting schedule {schedule_id}")

        # Get schedule manager
        manager = get_schedule_manager()

        # Verify schedule exists
        schedule = manager.get_schedule(schedule_id)
        if not schedule:
            return {
                "success": False,
                "error": f"Schedule not found: {schedule_id}"
            }

        # Delete schedule
        manager.delete_schedule(schedule_id)

        logger.info(f"Deleted schedule {schedule_id}")

        return {
            "success": True,
            "schedule_id": schedule_id,
            "deleted_schedule": {
                "sender_email": schedule.sender_email,
                "description": schedule.description
            }
        }

    except ScheduleError as e:
        logger.error(f"Failed to delete schedule: {e}")
        return {
            "success": False,
            "error": f"Failed to delete schedule: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Failed to delete schedule: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to delete schedule: {str(e)}"
        }


# Server startup
if __name__ == "__main__":
    # Initialize configuration
    config = get_app_config()
    logger.info("Secure Payslip Downloader MCP Server starting...")
    logger.info(f"Project root: {config.project_root}")
    logger.info(f"Download base: {config.download_base_path}")
    logger.info(f"Timezone: {config.timezone}")

    # Run server
    mcp.run()
