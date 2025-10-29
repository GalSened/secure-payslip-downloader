# Cron Job Setup Instructions

This guide explains how to set up the automated monthly payslip download using cron.

## Overview

The cron job runs `scripts/run_scheduled_downloads.py` which:
1. Reads all active schedules from `schedules/tasks.json`
2. For each schedule, searches Gmail for matching emails
3. Downloads PDF attachments to the configured directory
4. Logs results to `logs/cron.log`

## Prerequisites

Before setting up cron:
1. ✅ Complete OAuth authentication (`uv run python scripts/oauth_setup.py`)
2. ✅ Create at least one schedule using the MCP tool `create_monthly_schedule`
3. ✅ Verify the schedule exists: `uv run python scripts/run_scheduled_downloads.py --dry-run`

## Setup Steps

### Step 1: Edit Crontab

Open your crontab for editing:

```bash
crontab -e
```

### Step 2: Add Cron Entry

Add this line to run at 9:00 AM on the 11th of every month:

```bash
0 9 11 * * cd /Users/galsened/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1
```

**Explanation of cron syntax:**
- `0 9 11 * *` = Minute 0, Hour 9, Day 11, Any Month, Any Weekday
- `cd /Users/galsened/secure-payslip-downloader` = Change to project directory
- `uv run python scripts/run_scheduled_downloads.py` = Run the script with uv
- `>> logs/cron.log 2>&1` = Append stdout and stderr to log file

### Step 3: Verify Crontab

After saving, verify the entry was added:

```bash
crontab -l
```

You should see your new cron entry.

### Step 4: Test Manually

Before waiting for the scheduled time, test the script manually:

```bash
cd /Users/galsened/secure-payslip-downloader
uv run python scripts/run_scheduled_downloads.py
```

Check the output and verify:
- OAuth authentication works
- Schedules are loaded correctly
- Emails are searched (if any match)
- Downloads work (if any new files)

### Step 5: Check Logs

After the first scheduled run (or manual run), check the logs:

```bash
# View full log
cat logs/cron.log

# View last 50 lines
tail -50 logs/cron.log

# Follow log in real-time (during manual run)
tail -f logs/cron.log
```

## Cron Time Examples

If you need a different schedule:

```bash
# Every month on the 1st at midnight
0 0 1 * * cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

# Every month on the 15th at 2:30 PM
30 14 15 * * cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

# Every Monday at 9:00 AM (for weekly payslips)
0 9 * * 1 cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

# First day of every quarter at 10:00 AM
0 10 1 1,4,7,10 * cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1
```

## Troubleshooting

### Cron job not running

1. **Check cron is running:**
   ```bash
   # macOS
   sudo launchctl list | grep cron

   # Linux
   systemctl status cron
   ```

2. **Check cron logs:**
   ```bash
   # macOS
   log show --predicate 'process == "cron"' --last 1h

   # Linux
   grep CRON /var/log/syslog
   ```

3. **Verify full paths:** Cron runs with a minimal environment. Always use full absolute paths.

### Script fails when run by cron

1. **Test with cron environment:**
   ```bash
   env -i HOME=$HOME /bin/sh -c 'cd /Users/galsened/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py'
   ```

2. **Check permissions:**
   ```bash
   # Verify script is executable
   ls -l scripts/run_scheduled_downloads.py

   # Verify credentials permissions
   ls -l credentials/
   ```

3. **Check OAuth token:**
   ```bash
   # Verify token exists and is readable
   ls -l credentials/token.pickle

   # If missing, re-authenticate:
   uv run python scripts/oauth_setup.py
   ```

### No emails found

1. **Verify schedule parameters:**
   ```bash
   # List all schedules
   cat schedules/tasks.json | python -m json.tool
   ```

2. **Test search manually via MCP:**
   - Use Claude Desktop
   - Call `search_payslip_email` tool
   - Verify emails exist with the given criteria

3. **Check Gmail API quota:**
   - Visit Google Cloud Console
   - Check API usage and quotas
   - Ensure you haven't exceeded limits

### Downloads fail

1. **Check disk space:**
   ```bash
   df -h ~/Documents/Payslips
   ```

2. **Check directory permissions:**
   ```bash
   ls -ld ~/Documents/Payslips
   ls -ld ~/Documents/Payslips/2025
   ```

3. **Verify PDF validation:**
   - Check logs for "not a valid PDF" errors
   - Ensure attachments are actually PDF files

## Disabling Cron Job

To temporarily disable the cron job:

```bash
# Edit crontab
crontab -e

# Comment out the line (add # at the beginning)
# 0 9 11 * * cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

# Save and exit
```

To completely remove:

```bash
# Edit crontab
crontab -e

# Delete the line entirely

# Save and exit
```

## Security Notes

1. **Credentials Security:**
   - Never commit `credentials/` directory to git (already in .gitignore)
   - Keep credentials directory permissions at 0700
   - Keep token.pickle permissions at 0600

2. **Log Security:**
   - Logs may contain email addresses and file names
   - Review logs periodically and rotate/delete old ones
   - Credentials are automatically redacted in logs

3. **Cron Environment:**
   - Cron runs with minimal environment variables
   - OAuth token path is resolved from project directory
   - All paths should be absolute for reliability

## Additional Resources

- Cron syntax: https://crontab.guru/
- Gmail API quotas: https://developers.google.com/gmail/api/reference/quota
- uv documentation: https://docs.astral.sh/uv/
