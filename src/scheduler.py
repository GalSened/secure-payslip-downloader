"""
Schedule management for automated payslip downloads.

This module handles:
- JSON-based schedule storage (schedules/tasks.json)
- CRUD operations for scheduled tasks
- Schedule validation
- Thread-safe file operations

Schedule Format:
    {
        "schedule_id": {
            "sender_email": "payroll@company.com",
            "subject_keywords": "payslip",
            "schedule": "0 9 11 * *",  # Cron format: minute hour day month weekday
            "enabled": true,
            "created_at": "2025-01-15T10:30:00",
            "last_run": null,
            "description": "Monthly payslip from Company Ltd"
        }
    }
"""

import json
import fcntl
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

from config import get_config, get_logger
from security import create_secure_file

logger = get_logger(__name__)


class ScheduleError(Exception):
    """Raised when schedule operations fail."""
    pass


class ValidationError(Exception):
    """Raised when schedule validation fails."""
    pass


@dataclass
class Schedule:
    """
    Represents a scheduled payslip download task.

    Attributes:
        schedule_id: Unique identifier for the schedule
        sender_email: Email address to search for payslips from
        subject_keywords: Optional keywords to match in subject line
        schedule: Cron schedule string (e.g., "0 9 11 * *")
        enabled: Whether the schedule is active
        created_at: ISO timestamp when schedule was created
        last_run: ISO timestamp of last successful run (None if never run)
        description: Human-readable description of the schedule
    """
    schedule_id: str
    sender_email: str
    subject_keywords: Optional[str]
    schedule: str
    enabled: bool
    created_at: str
    last_run: Optional[str]
    description: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert schedule to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Schedule':
        """Create Schedule from dictionary."""
        return cls(**data)


def validate_cron_schedule(schedule: str) -> bool:
    """
    Validate cron schedule format.

    Expected format: "minute hour day month weekday"
    Example: "0 9 11 * *" (9:00 AM on 11th of every month)

    Args:
        schedule: Cron schedule string

    Returns:
        True if valid

    Raises:
        ValidationError: If schedule format is invalid
    """
    parts = schedule.split()

    if len(parts) != 5:
        raise ValidationError(
            f"Invalid cron format. Expected 5 fields, got {len(parts)}. "
            f"Format: 'minute hour day month weekday'"
        )

    minute, hour, day, month, weekday = parts

    # Validate minute (0-59 or *)
    if minute != '*':
        try:
            min_val = int(minute)
            if not (0 <= min_val <= 59):
                raise ValidationError(f"Minute must be 0-59, got: {minute}")
        except ValueError:
            raise ValidationError(f"Invalid minute value: {minute}")

    # Validate hour (0-23 or *)
    if hour != '*':
        try:
            hour_val = int(hour)
            if not (0 <= hour_val <= 23):
                raise ValidationError(f"Hour must be 0-23, got: {hour}")
        except ValueError:
            raise ValidationError(f"Invalid hour value: {hour}")

    # Validate day (1-31 or *)
    if day != '*':
        try:
            day_val = int(day)
            if not (1 <= day_val <= 31):
                raise ValidationError(f"Day must be 1-31, got: {day}")
        except ValueError:
            raise ValidationError(f"Invalid day value: {day}")

    # Validate month (1-12 or *)
    if month != '*':
        try:
            month_val = int(month)
            if not (1 <= month_val <= 12):
                raise ValidationError(f"Month must be 1-12, got: {month}")
        except ValueError:
            raise ValidationError(f"Invalid month value: {month}")

    # Validate weekday (0-7 or * where 0=Sunday, 7=Sunday)
    if weekday != '*':
        try:
            weekday_val = int(weekday)
            if not (0 <= weekday_val <= 7):
                raise ValidationError(f"Weekday must be 0-7, got: {weekday}")
        except ValueError:
            raise ValidationError(f"Invalid weekday value: {weekday}")

    return True


def validate_email(email: str) -> bool:
    """
    Basic email validation.

    Args:
        email: Email address to validate

    Returns:
        True if valid

    Raises:
        ValidationError: If email format is invalid
    """
    if not email or '@' not in email:
        raise ValidationError(f"Invalid email address: {email}")

    local, domain = email.rsplit('@', 1)

    if not local or not domain:
        raise ValidationError(f"Invalid email address: {email}")

    if '.' not in domain:
        raise ValidationError(f"Invalid email domain: {domain}")

    return True


class ScheduleManager:
    """
    Manages scheduled payslip download tasks.

    Provides thread-safe CRUD operations for schedules stored in JSON format.
    Uses file locking to prevent concurrent modification issues.
    """

    def __init__(self, schedules_file: Optional[Path] = None):
        """
        Initialize schedule manager.

        Args:
            schedules_file: Path to schedules JSON file (optional, uses config default)
        """
        self.config = get_config()
        self.schedules_file = schedules_file or self.config.get_schedules_file()

        # Ensure schedules directory exists with secure permissions
        self.schedules_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

        # Initialize empty schedules file if it doesn't exist
        if not self.schedules_file.exists():
            self._write_schedules({})
            logger.info(f"Initialized schedules file: {self.schedules_file}")

    def _read_schedules(self) -> Dict[str, Dict[str, Any]]:
        """
        Read schedules from JSON file with file locking.

        Returns:
            Dictionary of schedules keyed by schedule_id

        Raises:
            ScheduleError: If file cannot be read
        """
        try:
            with open(self.schedules_file, 'r') as f:
                # Acquire shared lock for reading
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data if data else {}
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse schedules JSON: {e}")
            raise ScheduleError(f"Corrupted schedules file: {e}") from e
        except Exception as e:
            logger.error(f"Failed to read schedules: {e}")
            raise ScheduleError(f"Failed to read schedules: {e}") from e

    def _write_schedules(self, schedules: Dict[str, Dict[str, Any]]) -> None:
        """
        Write schedules to JSON file with file locking.

        Args:
            schedules: Dictionary of schedules to write

        Raises:
            ScheduleError: If file cannot be written
        """
        try:
            # Convert to JSON with pretty formatting
            json_data = json.dumps(schedules, indent=2, sort_keys=True)

            # Write with secure permissions
            create_secure_file(self.schedules_file, json_data.encode('utf-8'))

            logger.debug(f"Wrote {len(schedules)} schedules to {self.schedules_file}")

        except Exception as e:
            logger.error(f"Failed to write schedules: {e}")
            raise ScheduleError(f"Failed to write schedules: {e}") from e

    def create_schedule(
        self,
        sender_email: str,
        schedule: str,
        subject_keywords: Optional[str] = None,
        description: Optional[str] = None,
        enabled: bool = True
    ) -> str:
        """
        Create a new scheduled task.

        Args:
            sender_email: Email address to search for payslips from
            schedule: Cron schedule string (e.g., "0 9 11 * *")
            subject_keywords: Optional keywords to match in subject line
            description: Human-readable description
            enabled: Whether schedule is active (default: True)

        Returns:
            Schedule ID (UUID)

        Raises:
            ValidationError: If parameters are invalid
            ScheduleError: If schedule cannot be saved
        """
        # Validate inputs
        validate_email(sender_email)
        validate_cron_schedule(schedule)

        # Generate unique ID
        schedule_id = str(uuid.uuid4())

        # Create schedule object
        new_schedule = Schedule(
            schedule_id=schedule_id,
            sender_email=sender_email,
            subject_keywords=subject_keywords,
            schedule=schedule,
            enabled=enabled,
            created_at=datetime.now().isoformat(),
            last_run=None,
            description=description or f"Payslips from {sender_email}"
        )

        # Add to schedules
        schedules = self._read_schedules()
        schedules[schedule_id] = new_schedule.to_dict()
        self._write_schedules(schedules)

        logger.info(
            f"Created schedule {schedule_id}: "
            f"{sender_email} @ {schedule} (enabled={enabled})"
        )

        return schedule_id

    def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Get a specific schedule by ID.

        Args:
            schedule_id: Schedule ID to retrieve

        Returns:
            Schedule object or None if not found
        """
        schedules = self._read_schedules()
        schedule_data = schedules.get(schedule_id)

        if schedule_data:
            return Schedule.from_dict(schedule_data)

        return None

    def list_schedules(self, enabled_only: bool = False) -> List[Schedule]:
        """
        List all schedules.

        Args:
            enabled_only: If True, only return enabled schedules

        Returns:
            List of Schedule objects
        """
        schedules = self._read_schedules()

        schedule_list = []
        for schedule_data in schedules.values():
            schedule = Schedule.from_dict(schedule_data)
            if not enabled_only or schedule.enabled:
                schedule_list.append(schedule)

        # Sort by created_at
        schedule_list.sort(key=lambda s: s.created_at, reverse=True)

        return schedule_list

    def update_schedule(
        self,
        schedule_id: str,
        sender_email: Optional[str] = None,
        schedule: Optional[str] = None,
        subject_keywords: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """
        Update an existing schedule.

        Args:
            schedule_id: Schedule ID to update
            sender_email: New email (optional)
            schedule: New cron schedule (optional)
            subject_keywords: New keywords (optional)
            description: New description (optional)
            enabled: New enabled status (optional)

        Returns:
            True if updated successfully

        Raises:
            ScheduleError: If schedule not found or validation fails
        """
        schedules = self._read_schedules()

        if schedule_id not in schedules:
            raise ScheduleError(f"Schedule not found: {schedule_id}")

        # Validate new values
        if sender_email:
            validate_email(sender_email)
        if schedule:
            validate_cron_schedule(schedule)

        # Update fields
        schedule_data = schedules[schedule_id]

        if sender_email:
            schedule_data['sender_email'] = sender_email
        if schedule:
            schedule_data['schedule'] = schedule
        if subject_keywords is not None:  # Allow empty string to clear
            schedule_data['subject_keywords'] = subject_keywords
        if description:
            schedule_data['description'] = description
        if enabled is not None:
            schedule_data['enabled'] = enabled

        self._write_schedules(schedules)

        logger.info(f"Updated schedule {schedule_id}")
        return True

    def delete_schedule(self, schedule_id: str) -> bool:
        """
        Delete a schedule.

        Args:
            schedule_id: Schedule ID to delete

        Returns:
            True if deleted successfully

        Raises:
            ScheduleError: If schedule not found
        """
        schedules = self._read_schedules()

        if schedule_id not in schedules:
            raise ScheduleError(f"Schedule not found: {schedule_id}")

        del schedules[schedule_id]
        self._write_schedules(schedules)

        logger.info(f"Deleted schedule {schedule_id}")
        return True

    def mark_run(self, schedule_id: str, timestamp: Optional[str] = None) -> bool:
        """
        Mark a schedule as having been run.

        Args:
            schedule_id: Schedule ID
            timestamp: ISO timestamp (defaults to now)

        Returns:
            True if updated successfully

        Raises:
            ScheduleError: If schedule not found
        """
        schedules = self._read_schedules()

        if schedule_id not in schedules:
            raise ScheduleError(f"Schedule not found: {schedule_id}")

        schedules[schedule_id]['last_run'] = timestamp or datetime.now().isoformat()
        self._write_schedules(schedules)

        logger.debug(f"Marked schedule {schedule_id} as run")
        return True

    def get_active_schedules(self) -> List[Schedule]:
        """
        Get all enabled schedules.

        Returns:
            List of enabled Schedule objects
        """
        return self.list_schedules(enabled_only=True)

    def count_schedules(self) -> Dict[str, int]:
        """
        Get schedule statistics.

        Returns:
            Dictionary with counts: total, enabled, disabled
        """
        schedules = self.list_schedules(enabled_only=False)

        return {
            'total': len(schedules),
            'enabled': sum(1 for s in schedules if s.enabled),
            'disabled': sum(1 for s in schedules if not s.enabled)
        }
