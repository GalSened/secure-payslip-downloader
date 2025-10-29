#!/usr/bin/env python3
"""
Cron Runner Script for Scheduled Payslip Downloads

This script runs automatically via cron to download payslips based on
scheduled tasks. It reads active schedules from schedules/tasks.json
and downloads any matching payslips from Gmail.

Usage:
    uv run python scripts/run_scheduled_downloads.py

Cron Setup:
    # Run at 9:00 AM on the 11th of every month
    0 9 11 * * cd /path/to/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

Environment:
    - Requires OAuth token to be already set up (run oauth_setup.py first)
    - Uses configuration from environment variables or defaults
    - Logs to logs/cron.log and logs/app.log
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scheduler import ScheduleManager, Schedule
from gmail_client import GmailClient, GmailAPIError, GmailAuthError
from config import get_config
from security import setup_secure_logging


def setup_logging() -> logging.Logger:
    """
    Setup logging for cron execution.

    Returns:
        Logger instance
    """
    config = get_config()

    # Setup secure logging with both console and file
    setup_secure_logging(config.log_dir, config.log_level)

    logger = logging.getLogger(__name__)
    logger.info("=" * 70)
    logger.info("Starting scheduled payslip downloads")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 70)

    return logger


def download_payslips_for_schedule(
    gmail_client: GmailClient,
    schedule: Schedule,
    config,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Download payslips for a specific schedule.

    Args:
        gmail_client: Gmail API client
        schedule: Schedule to process
        config: Configuration object
        logger: Logger instance

    Returns:
        Dictionary with download results:
        {
            'success': bool,
            'emails_found': int,
            'downloads': int,
            'errors': List[str]
        }
    """
    result = {
        'success': False,
        'emails_found': 0,
        'downloads': 0,
        'errors': []
    }

    try:
        logger.info(f"Processing schedule: {schedule.description}")
        logger.info(f"  Sender: {schedule.sender_email}")
        logger.info(f"  Subject keywords: {schedule.subject_keywords or '(none)'}")

        # Search for emails (last 30 days by default)
        emails = gmail_client.search_emails(
            sender_email=schedule.sender_email,
            subject_keywords=schedule.subject_keywords,
            days_back=30
        )

        result['emails_found'] = len(emails)
        logger.info(f"  Found {len(emails)} matching emails")

        if not emails:
            logger.info("  No emails found, nothing to download")
            result['success'] = True
            return result

        # Process each email
        for email in emails:
            try:
                logger.info(f"  Processing email: {email['subject']}")
                logger.info(f"    Date: {email['date']}")
                logger.info(f"    Attachments: {len(email['attachments'])}")

                # Download each attachment
                for attachment in email['attachments']:
                    try:
                        filename = attachment['filename']
                        attachment_id = attachment['attachment_id']
                        size = attachment.get('size', 0)

                        logger.info(f"    Downloading: {filename} ({size} bytes)")

                        # Get year from email date for directory organization
                        try:
                            email_date = datetime.fromisoformat(email['date'])
                            year = email_date.year
                        except:
                            year = datetime.now().year

                        # Get download path
                        output_path = config.get_download_path(year, filename)

                        # Check if already downloaded
                        if output_path.exists():
                            logger.info(f"      Skipping: File already exists at {output_path}")
                            continue

                        # Download attachment
                        gmail_client.download_attachment(
                            message_id=email['id'],
                            attachment_id=attachment_id,
                            output_path=output_path
                        )

                        result['downloads'] += 1
                        logger.info(f"      ✓ Downloaded to: {output_path}")

                    except Exception as e:
                        error_msg = f"Failed to download {filename}: {e}"
                        logger.error(f"      ✗ {error_msg}")
                        result['errors'].append(error_msg)

            except Exception as e:
                error_msg = f"Failed to process email {email.get('id', 'unknown')}: {e}"
                logger.error(f"  ✗ {error_msg}")
                result['errors'].append(error_msg)

        # Mark as successful if we processed all emails (even if some downloads failed)
        if result['downloads'] > 0 or result['emails_found'] == 0:
            result['success'] = True

    except GmailAPIError as e:
        error_msg = f"Gmail API error: {e}"
        logger.error(f"  ✗ {error_msg}")
        result['errors'].append(error_msg)
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        logger.error(f"  ✗ {error_msg}", exc_info=True)
        result['errors'].append(error_msg)

    return result


def process_all_schedules(
    schedule_manager: ScheduleManager,
    gmail_client: GmailClient,
    config,
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Process all active schedules.

    Args:
        schedule_manager: Schedule manager instance
        gmail_client: Gmail client instance
        config: Configuration object
        logger: Logger instance

    Returns:
        Summary of all downloads
    """
    summary = {
        'total_schedules': 0,
        'processed': 0,
        'failed': 0,
        'total_emails': 0,
        'total_downloads': 0,
        'errors': []
    }

    try:
        # Get active schedules
        schedules = schedule_manager.get_active_schedules()
        summary['total_schedules'] = len(schedules)

        if not schedules:
            logger.info("No active schedules found")
            return summary

        logger.info(f"Found {len(schedules)} active schedule(s)")

        # Process each schedule
        for schedule in schedules:
            logger.info("")  # Blank line for readability

            result = download_payslips_for_schedule(
                gmail_client, schedule, config, logger
            )

            # Update summary
            summary['total_emails'] += result['emails_found']
            summary['total_downloads'] += result['downloads']
            summary['errors'].extend(result['errors'])

            if result['success']:
                summary['processed'] += 1

                # Mark schedule as run
                try:
                    schedule_manager.mark_run(schedule.schedule_id)
                    logger.info(f"  ✓ Marked schedule as run")
                except Exception as e:
                    logger.warning(f"  Failed to mark schedule as run: {e}")
            else:
                summary['failed'] += 1
                logger.error(f"  ✗ Schedule processing failed")

    except Exception as e:
        error_msg = f"Failed to process schedules: {e}"
        logger.error(error_msg, exc_info=True)
        summary['errors'].append(error_msg)

    return summary


def print_summary(summary: Dict[str, Any], logger: logging.Logger):
    """
    Print execution summary.

    Args:
        summary: Summary dictionary
        logger: Logger instance
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info("EXECUTION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Active schedules: {summary['total_schedules']}")
    logger.info(f"Processed successfully: {summary['processed']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Total emails found: {summary['total_emails']}")
    logger.info(f"Total downloads: {summary['total_downloads']}")

    if summary['errors']:
        logger.info(f"Errors: {len(summary['errors'])}")
        for i, error in enumerate(summary['errors'], 1):
            logger.error(f"  {i}. {error}")
    else:
        logger.info("Errors: 0")

    logger.info("=" * 70)


def main():
    """
    Main execution flow.

    Returns:
        0 on success, 1 on failure
    """
    logger = setup_logging()

    try:
        # Get configuration
        config = get_config()
        logger.info(f"Configuration loaded")
        logger.info(f"  Download base: {config.download_base_path}")
        logger.info(f"  Timezone: {config.timezone}")

        # Initialize managers
        schedule_manager = ScheduleManager()
        logger.info(f"Schedule manager initialized")

        gmail_client = GmailClient()
        logger.info(f"Gmail client initialized")

        # Verify authentication
        try:
            gmail_client.get_service()
            logger.info(f"Gmail authentication verified")
        except GmailAuthError as e:
            logger.error(f"Gmail authentication failed: {e}")
            logger.error("Run scripts/oauth_setup.py to authenticate")
            return 1

        # Process all schedules
        summary = process_all_schedules(
            schedule_manager, gmail_client, config, logger
        )

        # Print summary
        print_summary(summary, logger)

        # Determine exit code
        if summary['failed'] > 0:
            logger.warning("Some schedules failed to process")
            return 1
        elif summary['total_downloads'] == 0 and summary['total_emails'] > 0:
            logger.warning("No new downloads (all files may already exist)")
            return 0
        else:
            logger.info("All schedules processed successfully")
            return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
