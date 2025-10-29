# Secure Payslip Downloader

**Automated monthly payslip downloads from Gmail with Claude Desktop integration.**

A secure MCP (Model Context Protocol) server that automatically downloads PDF payslips from Gmail using OAuth authentication, with support for scheduled downloads via cron.

## ✨ Features

- 🔒 **Secure OAuth 2.0 Authentication** - Gmail API with read-only access
- 📅 **Automated Monthly Downloads** - Set and forget with system cron
- 🤖 **Claude Desktop Integration** - 5 MCP tools for interactive management
- 📁 **Organized Storage** - Files saved by year: `~/Documents/Payslips/YYYY/`
- 🔐 **Security-First Design** - File permissions, path traversal prevention, credential redaction
- 📄 **PDF Validation** - Magic bytes validation ensures only PDFs are downloaded
- 🌍 **Timezone Support** - Configured for Israel timezone (Asia/Jerusalem)
- 📊 **Comprehensive Logging** - All operations logged with sensitive data redacted

## 🏗️ Architecture

```
secure-payslip-downloader/
├── src/
│   ├── server.py           # FastMCP server with 5 tools
│   ├── gmail_client.py     # Gmail API with OAuth & rate limiting
│   ├── scheduler.py        # Schedule management (JSON-based)
│   ├── config.py           # Configuration management
│   └── security.py         # Security utilities
├── scripts/
│   ├── oauth_setup.py              # OAuth authentication wizard
│   ├── run_scheduled_downloads.py  # Cron runner script
│   └── test_scheduler.py           # Scheduler tests
├── credentials/            # OAuth credentials (gitignored)
├── schedules/              # Schedule storage (gitignored)
├── logs/                   # Application logs (gitignored)
└── pyproject.toml          # uv dependencies

```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.9+** with [uv](https://docs.astral.sh/uv/) installed
2. **Google Cloud project** with Gmail API enabled
3. **Claude Desktop** (for MCP integration)

### Installation

```bash
# 1. Clone or navigate to project directory
cd /Users/galsened/secure-payslip-downloader

# 2. Install dependencies (already done if using uv)
uv sync

# 3. Set up Google OAuth (see GOOGLE_CLOUD_SETUP.md)
# Download credentials.json to credentials/

# 4. Run OAuth setup
uv run python scripts/oauth_setup.py

# 5. Add MCP server to Claude Desktop
# See "Claude Desktop Configuration" section below
```

### Claude Desktop Configuration

Add this to your `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "secure-payslip-downloader": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/galsened/secure-payslip-downloader",
        "run",
        "python",
        "src/server.py"
      ],
      "env": {
        "GMAIL_CREDS_PATH": "/Users/galsened/secure-payslip-downloader/credentials/credentials.json",
        "DOWNLOAD_BASE_PATH": "/Users/galsened/Documents/Payslips",
        "TIMEZONE": "Asia/Jerusalem",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Note:** Update paths if you installed to a different location.

## 🛠️ MCP Tools

The server provides 5 tools accessible through Claude Desktop:

### 1. `search_payslip_email`

Search for payslip emails from a specific sender.

```javascript
search_payslip_email(
  sender_email="payroll@company.com",
  subject_keywords="payslip",  // optional
  days_back=30                 // optional
)
```

**Returns:** List of matching emails with attachment metadata.

### 2. `download_payslip`

Download a specific PDF attachment.

```javascript
download_payslip(
  message_id="18f3a4b5c6d7e8f9",
  attachment_id="ANGjdJ8...",
  filename="Payslip_November_2025.pdf"
)
```

**Returns:** Download status and file path.

### 3. `create_monthly_schedule`

Create an automated monthly download schedule.

```javascript
create_monthly_schedule(
  sender_email="payroll@company.com",
  day_of_month=11,
  hour=9,                      // optional, default: 9
  minute=0,                    // optional, default: 0
  subject_keywords="payslip",  // optional
  description="Monthly payslip from Company Ltd"  // optional
)
```

**Returns:** Schedule ID and cron setup instructions.

### 4. `list_schedules`

List all configured schedules.

```javascript
list_schedules(
  enabled_only=false  // optional
)
```

**Returns:** All schedules with status and statistics.

### 5. `delete_schedule`

Remove a scheduled download.

```javascript
delete_schedule(
  schedule_id="abc123..."
)
```

**Returns:** Deletion confirmation.

## 📅 Setting Up Automated Downloads

### Step 1: Create Schedule via Claude

```
You: Create a monthly schedule to download payslips from payroll@company.com
     on the 11th of each month at 9 AM with subject keyword "payslip"
```

Claude will use the `create_monthly_schedule` tool and return the cron command.

### Step 2: Add to Crontab

```bash
# Edit crontab
crontab -e

# Add the cron command from Step 1 (example):
0 9 11 * * cd /Users/galsened/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

# Save and exit
```

### Step 3: Verify

```bash
# Check crontab entry
crontab -l

# Test manually
uv run python scripts/run_scheduled_downloads.py

# Check logs
tail -f logs/cron.log
```

For detailed cron setup instructions, see [CRON_SETUP.md](CRON_SETUP.md).

## 📖 Usage Examples

### Example 1: One-Time Download

```
You: Search for payslips from payroll@mycompany.com in the last 7 days

Claude: [Uses search_payslip_email tool]
        Found 1 email with 1 PDF attachment: "Payslip_November_2025.pdf"

You: Download it

Claude: [Uses download_payslip tool]
        Downloaded to: ~/Documents/Payslips/2025/Payslip_November_2025.pdf
```

### Example 2: Set Up Automation

```
You: Set up automatic monthly download from hr@company.com on the 11th at 9 AM

Claude: [Uses create_monthly_schedule tool]
        Schedule created! Add this to your crontab:
        0 9 11 * * cd /path/to/project && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1

You: [Adds to crontab]
```

### Example 3: Manage Schedules

```
You: Show me all my scheduled downloads

Claude: [Uses list_schedules tool]
        You have 2 active schedules:
        1. Company A payslips - Every 11th at 09:00
        2. Company B payslips - Every 15th at 14:00

You: Delete the first one

Claude: [Uses delete_schedule tool]
        Schedule deleted successfully
```

## 🔒 Security Features

### Authentication
- **OAuth 2.0 only** - No passwords or API keys
- **Gmail readonly scope** - Cannot modify or delete emails
- **Secure token storage** - 0600 permissions on token.pickle
- **Automatic token refresh** - No manual intervention needed

### File Security
- **Path traversal prevention** - Filename sanitization
- **Secure permissions** - 0700 on sensitive directories, 0600 on files
- **PDF validation** - Magic bytes check (%PDF-)
- **Organized storage** - Files grouped by year

### Logging Security
- **Credential redaction** - Tokens, passwords, API keys masked
- **Email partial redaction** - Only domains shown in logs
- **Secure log permissions** - 0700 on logs directory

### Rate Limiting
- **5 calls/second** for search operations
- **3 calls/second** for downloads
- **Exponential backoff** for API errors (429, 500, 503)

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Test scheduler module
uv run python scripts/test_scheduler.py

# Test OAuth setup (requires credentials.json)
uv run python scripts/oauth_setup.py

# Test cron runner (requires OAuth token)
uv run python scripts/run_scheduled_downloads.py

# Verify MCP server
uv run python -c "import sys; sys.path.insert(0, 'src'); from server import mcp; print('✓ MCP server OK')"
```

## 📁 File Organization

### Downloads

```
~/Documents/Payslips/
├── 2024/
│   ├── Payslip_December_2024.pdf
│   └── Payslip_November_2024.pdf
└── 2025/
    ├── Payslip_January_2025.pdf
    └── Payslip_February_2025.pdf
```

### Schedules

Stored in `schedules/tasks.json`:

```json
{
  "abc123-456": {
    "sender_email": "payroll@company.com",
    "subject_keywords": "payslip",
    "schedule": "0 9 11 * *",
    "enabled": true,
    "created_at": "2025-01-15T10:30:00",
    "last_run": "2025-02-11T09:00:05",
    "description": "Monthly payslip from Company Ltd"
  }
}
```

### Logs

- `logs/app.log` - Application logs
- `logs/cron.log` - Cron execution logs

## ⚙️ Configuration

### Environment Variables

- `GMAIL_CREDS_PATH` - Path to credentials.json (default: `credentials/credentials.json`)
- `DOWNLOAD_BASE_PATH` - Base download directory (default: `~/Documents/Payslips`)
- `TIMEZONE` - Timezone for scheduling (default: `Asia/Jerusalem`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

### Directory Structure

Sensitive directories (credentials, schedules, logs) use 0700 permissions.
Download directory uses 0755 permissions.

## 🐛 Troubleshooting

### OAuth Authentication Fails

```bash
# Re-run OAuth setup
uv run python scripts/oauth_setup.py

# Check credentials exist
ls -l credentials/credentials.json

# Check permissions
chmod 600 credentials/credentials.json
```

### Cron Job Not Running

```bash
# Check crontab
crontab -l

# Check cron service (macOS)
sudo launchctl list | grep cron

# Check logs
tail -50 logs/cron.log

# Test manually
uv run python scripts/run_scheduled_downloads.py
```

### No Emails Found

```bash
# Test search via Claude Desktop
# Use: search_payslip_email tool

# Check Gmail API quota
# Visit: Google Cloud Console > APIs & Services > Quotas

# Verify sender email is exact
# Gmail search is case-sensitive for email addresses
```

### Downloads Fail

```bash
# Check disk space
df -h ~/Documents/Payslips

# Check permissions
ls -ld ~/Documents/Payslips
ls -ld ~/Documents/Payslips/2025

# Check logs for details
grep ERROR logs/app.log
```

## 📚 Documentation

- [CRON_SETUP.md](CRON_SETUP.md) - Detailed cron configuration guide
- [GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md) - Google Cloud project setup (coming soon)
- [.env.example](.env.example) - Environment variable template

## 🔗 Dependencies

- **fastmcp** - MCP server framework
- **google-auth** - OAuth authentication
- **google-api-python-client** - Gmail API client
- **python-dateutil** - Date/time utilities
- **pydantic** - Data validation

Full dependency list in `pyproject.toml`.

## 📋 Requirements

- Python 3.9 or higher
- macOS or Linux (Windows with WSL)
- Gmail account with OAuth credentials
- Claude Desktop (for MCP integration)

## 🤝 Contributing

This is a personal tool, but feel free to fork and adapt for your needs.

## 📄 License

MIT License - See LICENSE file for details.

## ⚠️ Important Notes

1. **OAuth Token Security:**
   - Never commit `credentials/` directory
   - Never share your `token.pickle` file
   - Token provides read-only Gmail access

2. **Cron Environment:**
   - Cron runs with minimal environment
   - Always use absolute paths
   - Test cron command manually first

3. **Gmail API Limits:**
   - Free tier: 1 billion quota units/day
   - Search: 5 units/request
   - Download: 10 units/request
   - Typical usage: ~1000 units/month

4. **File Organization:**
   - Files organized by email date year
   - Duplicate files automatically skipped
   - Original filenames preserved (sanitized)

## 🙏 Acknowledgments

Built with:
- [FastMCP](https://github.com/jlowin/fastmcp) by Marvin Prefect
- [Gmail API](https://developers.google.com/gmail/api) by Google
- [uv](https://docs.astral.sh/uv/) by Astral

---

**Status:** ✅ Fully Implemented and Tested

**Last Updated:** 2025-01-29

For support or questions, open an issue on GitHub.
