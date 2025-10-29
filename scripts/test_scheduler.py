#!/usr/bin/env python3
"""
Test script for scheduler.py

Verifies:
1. Schedule creation with validation
2. CRUD operations
3. JSON persistence
4. Active schedule filtering
5. Update and delete operations
"""

import sys
from pathlib import Path
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from scheduler import (
    ScheduleManager, Schedule, ValidationError, ScheduleError,
    validate_cron_schedule, validate_email
)


def test_cron_validation():
    """Test cron schedule validation."""
    print("Test 1: Cron schedule validation")

    valid_schedules = [
        "0 9 11 * *",  # 9 AM on 11th
        "30 14 * * 1",  # 2:30 PM every Monday
        "0 0 1 1 *",  # Midnight on Jan 1st
        "* * * * *",  # Every minute
    ]

    for schedule in valid_schedules:
        try:
            validate_cron_schedule(schedule)
            print(f"  ✓ Valid: {schedule}")
        except ValidationError as e:
            print(f"  ✗ Should be valid: {schedule} - {e}")
            return False

    invalid_schedules = [
        "0 9 11",  # Too few fields
        "0 9 11 * * *",  # Too many fields
        "60 9 11 * *",  # Invalid minute (>59)
        "0 25 11 * *",  # Invalid hour (>23)
        "0 9 32 * *",  # Invalid day (>31)
        "0 9 11 13 *",  # Invalid month (>12)
        "0 9 11 * 8",  # Invalid weekday (>7)
    ]

    for schedule in invalid_schedules:
        try:
            validate_cron_schedule(schedule)
            print(f"  ✗ Should be invalid: {schedule}")
            return False
        except ValidationError:
            print(f"  ✓ Correctly rejected: {schedule}")

    print("  ✓ All cron validation tests passed\n")
    return True


def test_email_validation():
    """Test email validation."""
    print("Test 2: Email validation")

    valid_emails = [
        "test@example.com",
        "user.name+tag@company.co.uk",
        "payroll@company-name.org",
    ]

    for email in valid_emails:
        try:
            validate_email(email)
            print(f"  ✓ Valid: {email}")
        except ValidationError as e:
            print(f"  ✗ Should be valid: {email} - {e}")
            return False

    invalid_emails = [
        "not-an-email",
        "@example.com",
        "user@",
        "user@domain",
        "",
    ]

    for email in invalid_emails:
        try:
            validate_email(email)
            print(f"  ✗ Should be invalid: {email}")
            return False
        except ValidationError:
            print(f"  ✓ Correctly rejected: {email}")

    print("  ✓ All email validation tests passed\n")
    return True


def test_schedule_crud():
    """Test CRUD operations."""
    print("Test 3: Schedule CRUD operations")

    # Create temp directory for testing
    temp_dir = Path(tempfile.mkdtemp())
    schedules_file = temp_dir / 'tasks.json'

    try:
        # Initialize manager
        manager = ScheduleManager(schedules_file=schedules_file)
        print("  ✓ ScheduleManager initialized")

        # CREATE: Add a schedule
        schedule_id = manager.create_schedule(
            sender_email="payroll@company.com",
            schedule="0 9 11 * *",
            subject_keywords="payslip",
            description="Monthly payslip"
        )
        print(f"  ✓ Created schedule: {schedule_id}")

        # READ: Get the schedule
        schedule = manager.get_schedule(schedule_id)
        assert schedule is not None, "Schedule not found"
        assert schedule.sender_email == "payroll@company.com"
        assert schedule.schedule == "0 9 11 * *"
        assert schedule.subject_keywords == "payslip"
        assert schedule.enabled == True
        print(f"  ✓ Retrieved schedule: {schedule.description}")

        # LIST: Get all schedules
        all_schedules = manager.list_schedules()
        assert len(all_schedules) == 1, f"Expected 1 schedule, got {len(all_schedules)}"
        print(f"  ✓ Listed schedules: {len(all_schedules)} total")

        # UPDATE: Modify the schedule
        manager.update_schedule(
            schedule_id,
            subject_keywords="salary slip",
            enabled=False
        )
        updated = manager.get_schedule(schedule_id)
        assert updated.subject_keywords == "salary slip"
        assert updated.enabled == False
        print(f"  ✓ Updated schedule: keywords={updated.subject_keywords}, enabled={updated.enabled}")

        # Active schedules filter
        active = manager.get_active_schedules()
        assert len(active) == 0, "Should have 0 active schedules"
        print(f"  ✓ Active schedules: {len(active)}")

        # Re-enable
        manager.update_schedule(schedule_id, enabled=True)
        active = manager.get_active_schedules()
        assert len(active) == 1, "Should have 1 active schedule"
        print(f"  ✓ Re-enabled schedule")

        # Mark as run
        manager.mark_run(schedule_id)
        ran = manager.get_schedule(schedule_id)
        assert ran.last_run is not None, "last_run should be set"
        print(f"  ✓ Marked schedule as run: {ran.last_run}")

        # DELETE: Remove the schedule
        manager.delete_schedule(schedule_id)
        deleted = manager.get_schedule(schedule_id)
        assert deleted is None, "Schedule should be deleted"
        print(f"  ✓ Deleted schedule")

        # Verify empty
        final = manager.list_schedules()
        assert len(final) == 0, "Should have 0 schedules"
        print(f"  ✓ All schedules cleared")

        print("  ✓ All CRUD tests passed\n")
        return True

    finally:
        # Cleanup
        shutil.rmtree(temp_dir)


def test_multiple_schedules():
    """Test managing multiple schedules."""
    print("Test 4: Multiple schedules")

    temp_dir = Path(tempfile.mkdtemp())
    schedules_file = temp_dir / 'tasks.json'

    try:
        manager = ScheduleManager(schedules_file=schedules_file)

        # Create 3 schedules
        ids = []
        for i in range(3):
            schedule_id = manager.create_schedule(
                sender_email=f"company{i}@example.com",
                schedule="0 9 11 * *",
                description=f"Company {i} payslip"
            )
            ids.append(schedule_id)
            print(f"  ✓ Created schedule {i+1}: {schedule_id[:8]}...")

        # List all
        all_schedules = manager.list_schedules()
        assert len(all_schedules) == 3, f"Expected 3 schedules, got {len(all_schedules)}"
        print(f"  ✓ Listed all schedules: {len(all_schedules)} total")

        # Disable one
        manager.update_schedule(ids[1], enabled=False)

        # Get active only
        active = manager.get_active_schedules()
        assert len(active) == 2, f"Expected 2 active, got {len(active)}"
        print(f"  ✓ Active schedules: {len(active)}")

        # Get counts
        counts = manager.count_schedules()
        assert counts['total'] == 3
        assert counts['enabled'] == 2
        assert counts['disabled'] == 1
        print(f"  ✓ Counts: {counts}")

        # Delete all
        for schedule_id in ids:
            manager.delete_schedule(schedule_id)
        print(f"  ✓ Deleted all schedules")

        print("  ✓ Multiple schedules test passed\n")
        return True

    finally:
        shutil.rmtree(temp_dir)


def test_persistence():
    """Test that schedules persist across manager instances."""
    print("Test 5: Schedule persistence")

    temp_dir = Path(tempfile.mkdtemp())
    schedules_file = temp_dir / 'tasks.json'

    try:
        # Create schedule with first manager
        manager1 = ScheduleManager(schedules_file=schedules_file)
        schedule_id = manager1.create_schedule(
            sender_email="persistent@example.com",
            schedule="0 9 11 * *",
            description="Persistent schedule"
        )
        print(f"  ✓ Created schedule with manager1: {schedule_id[:8]}...")

        # Read with second manager (simulating new process)
        manager2 = ScheduleManager(schedules_file=schedules_file)
        schedule = manager2.get_schedule(schedule_id)
        assert schedule is not None, "Schedule should persist"
        assert schedule.sender_email == "persistent@example.com"
        print(f"  ✓ Retrieved schedule with manager2: {schedule.sender_email}")

        # Verify file exists and is readable
        assert schedules_file.exists(), "Schedules file should exist"
        import json
        with open(schedules_file, 'r') as f:
            data = json.load(f)
            assert schedule_id in data, "Schedule should be in file"
        print(f"  ✓ Verified JSON file contents")

        print("  ✓ Persistence test passed\n")
        return True

    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("  Scheduler Module Tests")
    print("=" * 70 + "\n")

    tests = [
        test_cron_validation,
        test_email_validation,
        test_schedule_crud,
        test_multiple_schedules,
        test_persistence,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
                print(f"  ✗ {test.__name__} FAILED\n")
        except Exception as e:
            failed += 1
            print(f"  ✗ {test.__name__} ERROR: {e}\n")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")

    if failed > 0:
        sys.exit(1)
    else:
        print("✅ All scheduler tests passed!")
        sys.exit(0)


if __name__ == '__main__':
    main()
