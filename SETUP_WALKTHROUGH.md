# Setup Walkthrough - Continue Working Guide

**Current Status:** OAuth credentials created in Google Cloud Console
**Next Step:** Download credentials.json and complete OAuth authentication

---

## 🎯 Where You Are Now

You have successfully completed:
- ✅ Created Google Cloud project "Payslip Downloader"
- ✅ Enabled Gmail API
- ✅ Configured OAuth consent screen
- ✅ Created OAuth 2.0 credentials (Desktop app)
- ✅ Client ID: `444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com`

**What's Next:** Download the credentials.json file and complete the setup process.

---

## 📥 Step 1: Download credentials.json

### Option A: From Google Cloud Console (Recommended)

1. **Open the Credentials page:**
   - Go to: https://console.cloud.google.com/apis/credentials?project=payslip-downloader-476606
   - Or navigate: Google Cloud Console → APIs & Services → Credentials

2. **Locate your OAuth client:**
   - Find "Secure Payslip Downloader Desktop" in the OAuth 2.0 Client IDs table
   - Client ID: `444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com`

3. **Download the credentials:**
   - **Method 1:** Click the client name (blue link) to open details, then click the download icon (⬇) at the top
   - **Method 2:** Click the edit icon (pencil) in the Actions column, then look for "DOWNLOAD JSON" button

4. **The downloaded file will be named:**
   ```
   client_secret_444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com.json
   ```

### Option B: Alternative Download Path

If you can't find the download button:

1. Click on the OAuth client name
2. On the details page, you should see:
   - **Client ID:** `444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com`
   - **Client secret:** (hidden by default, click "SHOW" to reveal)
3. Look for "Download OAuth client" or download icon in the top-right corner

### Verify the Download

```bash
# Check if the file was downloaded
ls -lh ~/Downloads/client_secret*.json

# Expected output: One file named like:
# client_secret_444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com.json
```

---

## 🔧 Step 2: Install credentials.json

Once you have the downloaded file, run these commands:

```bash
# 1. Navigate to Downloads folder
cd ~/Downloads

# 2. List the downloaded credential files
ls -lh client_secret*.json

# 3. Rename to credentials.json (use tab completion for the exact filename)
mv client_secret_444959234045-1mn2vh1pcu3m4l71gljubc74agh1mj7u.apps.googleusercontent.com.json credentials.json

# 4. Move to project credentials directory
mv credentials.json /Users/galsened/secure-payslip-downloader/credentials/

# 5. Set secure permissions (owner read/write only)
chmod 600 /Users/galsened/secure-payslip-downloader/credentials/credentials.json

# 6. Verify the file is in place with correct permissions
ls -l /Users/galsened/secure-payslip-downloader/credentials/credentials.json
```

**Expected output:**
```
-rw-------  1 galsened  staff  591 Oct 29 14:30 credentials.json
```

The `-rw-------` means:
- Owner (you) can read and write
- Group and others have no access

---

## 🔐 Step 3: Run OAuth Setup

Now authenticate with Gmail API:

```bash
# Navigate to project directory
cd /Users/galsened/secure-payslip-downloader

# Run OAuth setup wizard
uv run python scripts/oauth_setup.py
```

### What Happens Next:

1. **Browser Opens Automatically**
   - A browser window will open to Google's sign-in page
   - If it doesn't open automatically, copy the URL shown in the terminal

2. **Sign In**
   - Use your Gmail account: `galsened@gmail.com`
   - If already signed in, select your account

3. **Grant Permissions**
   - You'll see: "Secure Payslip Downloader wants to access your Google Account"
   - **Scopes requested:**
     - Read your email messages and settings (read-only)
     - View your email messages and settings
   - Click **"Allow"**

4. **OAuth Consent Warning**
   - You may see: "Google hasn't verified this app"
   - This is expected for personal use apps
   - Click **"Advanced"** → **"Go to Secure Payslip Downloader (unsafe)"**
   - Then click **"Allow"**

5. **Success Confirmation**
   - Browser shows: "The authentication flow has completed. You may close this window."
   - Terminal shows: ✓ Authentication successful!
   - A file `token.pickle` is created in `credentials/`

### Verify OAuth Success

```bash
# Check that token.pickle was created
ls -l credentials/token.pickle

# Expected output:
# -rw-------  1 galsened  staff  xxx Oct 29 14:35 token.pickle
```

---

## 🖥️ Step 4: Configure Claude Desktop

Add the MCP server to Claude Desktop:

```bash
# Open Claude Desktop config file
open -a TextEdit ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### Configuration to Add:

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

**If you already have other MCP servers configured:**

Just add the `secure-payslip-downloader` entry inside the existing `mcpServers` object:

```json
{
  "mcpServers": {
    "existing-server": {
      ...
    },
    "secure-payslip-downloader": {
      "command": "uv",
      ...
    }
  }
}
```

### Restart Claude Desktop

After saving the config:
1. Quit Claude Desktop completely (Cmd+Q)
2. Reopen Claude Desktop
3. Wait ~5 seconds for MCP servers to initialize

---

## ✅ Step 5: Test the Integration

### Test 1: Verify MCP Tools Are Available

In Claude Desktop, start a new conversation and type:

```
Show me the available MCP tools for payslip downloader
```

You should see **5 tools** listed:
1. `search_payslip_email` - Search for payslip emails
2. `download_payslip` - Download PDF attachments
3. `create_monthly_schedule` - Create automated schedule
4. `list_schedules` - List all schedules
5. `delete_schedule` - Remove a schedule

### Test 2: Search for Emails

Try searching for emails (replace with your actual payroll sender):

```
Search for payslip emails from payroll@mycompany.com in the last 30 days
```

**Expected result:**
- Claude will use the `search_payslip_email` tool
- You'll see either:
  - A list of matching emails with attachments
  - "No emails found" (if you don't have any yet)

### Test 3: Download a Payslip (if emails found)

If emails were found, try downloading:

```
Download the most recent payslip
```

**Expected result:**
- Claude will use the `download_payslip` tool
- File will be saved to: `~/Documents/Payslips/YYYY/filename.pdf`
- You'll get a confirmation with the file path

---

## 📅 Step 6: Create Automated Schedule

### Create Your First Schedule

In Claude Desktop:

```
Create a monthly schedule to download payslips from payroll@mycompany.com
on the 11th of each month at 9 AM with subject keyword "payslip"
```

**Expected result:**
- Claude will use `create_monthly_schedule` tool
- You'll get:
  - Schedule ID (save this!)
  - Cron command to add
  - Confirmation message

**Example response:**
```
Schedule created successfully!

Schedule ID: abc123-def456-ghi789
Sender: payroll@mycompany.com
Schedule: Every 11th of month at 09:00
Cron schedule: 0 9 11 * *

To enable automated downloads, add this to your crontab:
0 9 11 * * cd /Users/galsened/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1
```

---

## ⏰ Step 7: Set Up Cron Job

### Edit Crontab

```bash
# Open crontab editor
crontab -e
```

**If you've never used crontab before:**
- Default editor is usually `vi`
- Press `i` to enter insert mode
- Paste the cron command
- Press `Esc`, then type `:wq` and press Enter to save

### Add the Cron Command

Paste the command Claude gave you (example):

```cron
# Download payslips on the 11th of each month at 9 AM
0 9 11 * * cd /Users/galsened/secure-payslip-downloader && uv run python scripts/run_scheduled_downloads.py >> logs/cron.log 2>&1
```

**Breakdown of the cron schedule:**
```
0 9 11 * *
│ │ │  │ │
│ │ │  │ └─ Day of week (0-6, 0=Sunday, *=any)
│ │ │  └─── Month (1-12, *=any)
│ │ └────── Day of month (1-31)
│ └──────── Hour (0-23, 9=9 AM)
└────────── Minute (0-59, 0=on the hour)
```

### Verify Crontab

```bash
# List current crontab entries
crontab -l

# Expected output: Your cron command should be listed
```

### Grant Cron Permissions (macOS)

On macOS Ventura or later, you need to give cron permission:

1. **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Click the **+** button
3. Navigate to: `/usr/sbin/cron`
4. Add `/usr/sbin/cron` to the list
5. Restart cron (or restart your Mac)

**Alternative:** Give Terminal or iTerm2 Full Disk Access instead.

---

## 🧪 Step 8: Test Manual Run

Before waiting for the scheduled time, test the cron script manually:

```bash
# Navigate to project
cd /Users/galsened/secure-payslip-downloader

# Run the scheduled download script
uv run python scripts/run_scheduled_downloads.py

# Check logs
cat logs/cron.log
```

**Expected output (if schedules exist and emails found):**
```
2025-01-29 14:45:00 - INFO - Starting scheduled downloads...
2025-01-29 14:45:00 - INFO - Found 1 active schedule(s)
2025-01-29 14:45:01 - INFO - Processing schedule: abc123-def456-ghi789
2025-01-29 14:45:02 - INFO - Searching for emails from: payroll@***
2025-01-29 14:45:03 - INFO - Found 1 email(s) with attachments
2025-01-29 14:45:04 - INFO - Downloaded: Payslip_November_2025.pdf
2025-01-29 14:45:04 - INFO - Schedule completed successfully
```

**If no emails found yet:**
```
2025-01-29 14:45:00 - INFO - Starting scheduled downloads...
2025-01-29 14:45:00 - INFO - Found 1 active schedule(s)
2025-01-29 14:45:01 - INFO - Processing schedule: abc123-def456-ghi789
2025-01-29 14:45:02 - INFO - Searching for emails from: payroll@***
2025-01-29 14:45:03 - INFO - No emails found matching criteria
```

---

## 📊 Step 9: Verify Everything Works

### Check Downloaded Files

```bash
# List downloaded payslips
ls -lR ~/Documents/Payslips/

# Expected structure:
# ~/Documents/Payslips/
# ├── 2025/
# │   ├── Payslip_January_2025.pdf
# │   └── Payslip_February_2025.pdf
```

### Check Schedule Status

In Claude Desktop:

```
Show me all my scheduled downloads
```

**Expected result:**
- List of all schedules with details
- Last run timestamp
- Next run time (calculated from cron schedule)

### Monitor Logs

```bash
# Watch cron logs in real-time
tail -f logs/cron.log

# View application logs
tail -f logs/app.log

# Search for errors
grep ERROR logs/app.log
grep ERROR logs/cron.log
```

---

## 🎉 Success Checklist

- [ ] credentials.json file downloaded and installed
- [ ] OAuth token created (token.pickle exists)
- [ ] Claude Desktop configured with MCP server
- [ ] 5 MCP tools visible in Claude Desktop
- [ ] Successfully searched for emails via Claude
- [ ] Successfully downloaded at least one payslip
- [ ] Schedule created with valid cron syntax
- [ ] Cron job added to crontab
- [ ] Manual test run completed successfully
- [ ] Logs directory contains cron.log and app.log

---

## 🔍 Troubleshooting Common Issues

### Issue 1: "credentials.json not found"

**Solution:**
```bash
# Check if file exists
ls -l credentials/credentials.json

# If not, re-download from Google Cloud Console
# Make sure filename is exactly "credentials.json"
```

### Issue 2: "OAuth authentication failed"

**Solution:**
```bash
# Delete old token and re-authenticate
rm credentials/token.pickle
uv run python scripts/oauth_setup.py
```

### Issue 3: "MCP tools not showing in Claude Desktop"

**Solution:**
1. Check config file syntax (must be valid JSON)
2. Verify paths are absolute, not relative
3. Restart Claude Desktop completely (Cmd+Q, then reopen)
4. Check Claude Desktop logs: `~/Library/Logs/Claude/`

### Issue 4: "Cron job not running"

**Solution:**
```bash
# Test manually first
cd /Users/galsened/secure-payslip-downloader
uv run python scripts/run_scheduled_downloads.py

# Check cron permissions (macOS)
# System Settings → Privacy & Security → Full Disk Access
# Add: /usr/sbin/cron or Terminal.app

# Verify crontab entry
crontab -l

# Check system cron logs (macOS)
log show --predicate 'process == "cron"' --last 1h
```

### Issue 5: "No emails found"

**Reasons:**
- No emails from that sender in the specified time range
- Sender email doesn't match exactly (case-sensitive)
- Subject keywords don't match
- Emails are in a different folder (spam, archives)

**Solution:**
```bash
# Test search with broader criteria via Claude:
"Search for ANY emails from payroll@mycompany.com"

# Check Gmail manually to verify emails exist
# Try different sender variations:
# - payroll@company.com
# - no-reply@company.com
# - noreply@company.com
```

### Issue 6: "Permission denied" errors

**Solution:**
```bash
# Fix directory permissions
chmod 700 credentials schedules logs

# Fix file permissions
chmod 600 credentials/credentials.json
chmod 600 credentials/token.pickle
chmod 600 schedules/tasks.json

# Verify
ls -l credentials/ schedules/ logs/
```

---

## 📚 Additional Resources

### Documentation Files

- **README.md** - Complete project overview and usage guide
- **GOOGLE_CLOUD_SETUP.md** - Detailed OAuth setup with screenshots
- **CRON_SETUP.md** - Comprehensive cron configuration guide
- **VALIDATION_CHECKLIST.md** - Implementation status and test results
- **TEST_REPORT.md** - Complete testing documentation

### Testing Scripts

```bash
# Run setup verification
uv run python scripts/setup.py

# Test scheduler module
uv run python scripts/test_scheduler.py

# Test OAuth authentication
uv run python scripts/oauth_setup.py

# Test cron runner
uv run python scripts/run_scheduled_downloads.py
```

### Useful Commands

```bash
# Check Python version
python3 --version

# Check uv installation
uv --version

# Sync dependencies
uv sync

# View MCP server logs
tail -f logs/app.log

# View cron execution logs
tail -f logs/cron.log

# List active schedules
cat schedules/tasks.json | python3 -m json.tool

# Check Gmail API quota usage
# Visit: https://console.cloud.google.com/apis/api/gmail.googleapis.com/quotas
```

---

## 🚀 Next Steps After Setup

### 1. Add More Schedules

You can create multiple schedules for different payslip sources:

```
Create a schedule for payroll@company-a.com on the 11th at 9 AM
Create a schedule for hr@company-b.com on the 15th at 2 PM
```

Each schedule gets its own ID and can have different:
- Sender email
- Schedule timing
- Subject keywords
- Description

### 2. Organize Downloaded Files

Files are automatically organized by year:
```
~/Documents/Payslips/
├── 2024/
│   └── Payslip_December_2024.pdf
└── 2025/
    ├── Payslip_January_2025.pdf
    └── Payslip_February_2025.pdf
```

### 3. Monitor Usage

```bash
# Check how many times cron has run
grep "Starting scheduled downloads" logs/cron.log | wc -l

# Check total downloads
find ~/Documents/Payslips/ -name "*.pdf" | wc -l

# Check for errors
grep ERROR logs/cron.log logs/app.log
```

### 4. Backup Your Setup

```bash
# Backup schedules (JSON only, no credentials)
cp schedules/tasks.json ~/Backups/payslip-schedules-$(date +%Y%m%d).json

# Backup logs (optional)
tar -czf ~/Backups/payslip-logs-$(date +%Y%m%d).tar.gz logs/
```

---

## ⚠️ Security Best Practices

### Protect Your Credentials

```bash
# NEVER commit credentials to git
cat .gitignore | grep credentials
# Should show: credentials/

# Verify permissions
ls -la credentials/
# Should show: drwx------ (700) for directory
# Should show: -rw------- (600) for files

# NEVER share credentials.json or token.pickle
```

### Monitor Access

1. **Check OAuth token status:**
   - Visit: https://myaccount.google.com/permissions
   - Find "Secure Payslip Downloader"
   - Review last access time

2. **Revoke access if needed:**
   - Click "Remove Access" on the permissions page
   - Delete local tokens: `rm credentials/token.pickle`
   - Re-authenticate when needed

3. **Monitor API usage:**
   - Visit: https://console.cloud.google.com/apis/dashboard
   - Select "Payslip Downloader" project
   - Check Gmail API usage metrics

### Review Logs Regularly

```bash
# Check for suspicious activity
grep -i "error\|fail\|denied" logs/app.log

# Review access patterns
grep "Searching for emails" logs/cron.log | tail -20
```

---

## 📞 Getting Help

### Check Existing Documentation

1. Read README.md for complete usage guide
2. Check GOOGLE_CLOUD_SETUP.md for OAuth issues
3. Review CRON_SETUP.md for scheduling problems
4. Run `uv run python scripts/setup.py` for diagnostics

### Common Questions

**Q: Can I use this with multiple Gmail accounts?**
A: Yes, but you need separate OAuth tokens. Run `oauth_setup.py` for each account with different credentials.

**Q: What if I change my Gmail password?**
A: OAuth tokens are independent of your password. They remain valid unless revoked.

**Q: Can I search for emails from multiple senders?**
A: Create separate schedules for each sender. Each schedule runs independently.

**Q: How do I update the schedule timing?**
A: Delete the old schedule and create a new one with the desired timing.

**Q: Will this work on Windows?**
A: Partially. Core functionality works, but cron requires WSL (Windows Subsystem for Linux).

---

## 🎓 Understanding the System

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Desktop UI                        │
│  (User interacts via natural language)                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        │ MCP Protocol
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  FastMCP Server (src/server.py)              │
│                                                              │
│  Tools:                                                      │
│  • search_payslip_email                                      │
│  • download_payslip                                          │
│  • create_monthly_schedule                                   │
│  • list_schedules                                            │
│  • delete_schedule                                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ├──► Gmail API Client (src/gmail_client.py)
                        │    • OAuth authentication
                        │    • Rate limiting
                        │    • Email search
                        │    • Attachment download
                        │
                        └──► Schedule Manager (src/scheduler.py)
                             • CRUD operations
                             • JSON persistence
                             • Cron validation

┌─────────────────────────────────────────────────────────────┐
│                  Cron Job (System Scheduler)                 │
│  Runs: scripts/run_scheduled_downloads.py                    │
│  • Reads schedules from JSON                                 │
│  • Searches Gmail for matching emails                        │
│  • Downloads PDF attachments                                 │
│  • Updates last_run timestamps                               │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

**Interactive Download (via Claude Desktop):**
```
User → Claude Desktop → MCP Server → Gmail API → Download → Save File
```

**Automated Download (via Cron):**
```
Cron → run_scheduled_downloads.py → Scheduler → Gmail API → Download → Save File
```

### File Structure

```
secure-payslip-downloader/
├── src/                    # Source code
│   ├── server.py          # MCP server with 5 tools
│   ├── gmail_client.py    # Gmail API client
│   ├── scheduler.py       # Schedule manager
│   ├── config.py          # Configuration
│   └── security.py        # Security utilities
│
├── scripts/               # Utility scripts
│   ├── oauth_setup.py            # OAuth wizard
│   ├── run_scheduled_downloads.py # Cron runner
│   ├── test_scheduler.py         # Tests
│   └── setup.py                  # Verification
│
├── credentials/           # OAuth credentials (gitignored)
│   ├── credentials.json  # OAuth client config
│   └── token.pickle      # OAuth access token
│
├── schedules/             # Schedule storage (gitignored)
│   └── tasks.json        # Schedule definitions
│
├── logs/                  # Application logs (gitignored)
│   ├── app.log           # Application logs
│   └── cron.log          # Cron execution logs
│
└── docs/                  # Documentation
    ├── README.md
    ├── GOOGLE_CLOUD_SETUP.md
    ├── CRON_SETUP.md
    ├── SETUP_WALKTHROUGH.md (this file)
    ├── VALIDATION_CHECKLIST.md
    └── TEST_REPORT.md
```

---

## 🔄 Regular Maintenance

### Monthly Tasks

1. **Check downloaded files:**
   ```bash
   ls -lR ~/Documents/Payslips/
   ```

2. **Review logs for errors:**
   ```bash
   grep ERROR logs/cron.log logs/app.log
   ```

3. **Verify schedules are active:**
   ```
   # In Claude Desktop:
   Show me all my scheduled downloads
   ```

### Quarterly Tasks

1. **Review Google Cloud quota usage**
2. **Check OAuth token status**
3. **Backup schedules JSON file**
4. **Update project dependencies:**
   ```bash
   uv sync
   ```

### Annual Tasks

1. **Review and update schedules**
2. **Archive old payslips**
3. **Review security permissions**

---

**Status:** 🎯 **Ready to complete setup from Step 1**

**Last Updated:** 2025-01-29

**Next Action:** Download credentials.json from Google Cloud Console and follow Step 2

---

For questions or issues, refer to the troubleshooting section or check the comprehensive documentation in the README.md file.
