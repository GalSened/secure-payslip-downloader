# Google Cloud OAuth Setup Guide

This guide walks you through setting up Google Cloud credentials for the Gmail API.

## Overview

You need to:
1. Create a Google Cloud project
2. Enable the Gmail API
3. Configure the OAuth consent screen
4. Create OAuth credentials (Desktop app)
5. Download credentials.json

**Time required:** ~10 minutes

**Cost:** Free (Gmail API has generous free tier)

## Step-by-Step Instructions

### Step 1: Create Google Cloud Project

1. **Go to Google Cloud Console:**
   https://console.cloud.google.com/

2. **Sign in** with your Gmail account

3. **Create a new project:**
   - Click the project dropdown at the top
   - Click "New Project"
   - Enter project name: `Payslip Downloader`
   - Leave organization as "No organization"
   - Click "Create"

4. **Select your new project:**
   - Click the project dropdown again
   - Select "Payslip Downloader"

### Step 2: Enable Gmail API

1. **Go to APIs & Services:**
   - From the left menu, click "APIs & Services" → "Library"
   - Or visit: https://console.cloud.google.com/apis/library

2. **Search for Gmail API:**
   - In the search box, type "Gmail API"
   - Click on "Gmail API" from results

3. **Enable the API:**
   - Click the blue "Enable" button
   - Wait for it to enable (~30 seconds)

### Step 3: Configure OAuth Consent Screen

1. **Go to OAuth consent screen:**
   - From the left menu, click "OAuth consent screen"
   - Or visit: https://console.cloud.google.com/apis/credentials/consent

2. **Choose user type:**
   - Select "External" (even for personal use)
   - Click "Create"

3. **Fill in App information:**
   ```
   App name: Secure Payslip Downloader
   User support email: [your Gmail address]
   Developer contact email: [your Gmail address]
   ```

4. **Skip other optional fields:**
   - App domain, logo, etc. are optional
   - Click "Save and Continue"

5. **Add scopes:**
   - Click "Add or Remove Scopes"
   - Search for: `gmail.readonly`
   - Check: `.../auth/gmail.readonly` (Gmail read-only access)
   - Click "Update"
   - Click "Save and Continue"

6. **Add test users:**
   - Click "Add Users"
   - Enter your Gmail address
   - Click "Add"
   - Click "Save and Continue"

7. **Review summary:**
   - Review your settings
   - Click "Back to Dashboard"

### Step 4: Create OAuth Credentials

1. **Go to Credentials:**
   - From the left menu, click "Credentials"
   - Or visit: https://console.cloud.google.com/apis/credentials

2. **Create credentials:**
   - Click "Create Credentials" at the top
   - Select "OAuth client ID"

3. **Choose application type:**
   - Application type: **Desktop app**
   - Name: `Secure Payslip Downloader Desktop`
   - Click "Create"

4. **Download credentials:**
   - A dialog appears: "OAuth client created"
   - Click "Download JSON"
   - The file will be named something like: `client_secret_123456.json`

### Step 5: Install Credentials

1. **Rename the file:**
   ```bash
   cd ~/Downloads
   mv client_secret_*.json credentials.json
   ```

2. **Move to project:**
   ```bash
   mv credentials.json /Users/galsened/secure-payslip-downloader/credentials/
   ```

3. **Set permissions:**
   ```bash
   chmod 600 /Users/galsened/secure-payslip-downloader/credentials/credentials.json
   ```

4. **Verify placement:**
   ```bash
   ls -l /Users/galsened/secure-payslip-downloader/credentials/credentials.json
   ```

   Should show: `-rw------- 1 yourusername staff ...`

## Verification

After setup, verify everything works:

```bash
cd /Users/galsened/secure-payslip-downloader

# Run OAuth setup script
uv run python scripts/oauth_setup.py
```

You should see:
1. Browser opens automatically
2. Google sign-in page
3. "Secure Payslip Downloader wants to access your Google Account"
4. Click "Allow"
5. "The authentication flow has completed. You may close this window."
6. Terminal shows: ✓ Authentication successful!

## Understanding OAuth Scopes

The app requests **read-only** access to Gmail:

- ✅ **CAN:**
  - Read email metadata (sender, subject, date)
  - Search for emails
  - Download attachments
  - List messages

- ❌ **CANNOT:**
  - Send emails
  - Delete emails
  - Modify emails
  - Access contacts
  - Access Drive files
  - Access Calendar

## Security Best Practices

### 1. Protect credentials.json

```bash
# NEVER commit to git (already in .gitignore)
# NEVER share this file
# Keep permissions at 0600

# Verify .gitignore includes it:
grep credentials .gitignore
```

### 2. Protect token.pickle

```bash
# Generated after OAuth setup
# Contains your access token
# Auto-created with 0600 permissions

# Location:
ls -l credentials/token.pickle
```

### 3. Revoke access (if needed)

If you need to revoke access:

1. Visit: https://myaccount.google.com/permissions
2. Find "Secure Payslip Downloader"
3. Click "Remove Access"
4. Delete local tokens:
   ```bash
   rm credentials/token.pickle
   ```
5. Re-authenticate when needed

### 4. Monitor API usage

1. Visit: https://console.cloud.google.com/apis/dashboard
2. Select your project
3. View Gmail API usage metrics
4. Check for unusual activity

## Gmail API Quotas

### Free Tier Limits:

- **Quota units per day:** 1,000,000,000 (1 billion)
- **Per-user rate limit:** 250 quota units/second
- **Project rate limit:** Shared across all users

### Cost per operation:

- **Search emails:** 5 units/request
- **Get email details:** 5 units/request
- **Download attachment:** 10 units/request

### Typical usage for this app:

```
Monthly downloads (12 emails/year):
- 12 searches × 5 units = 60 units
- 12 details × 5 units = 60 units
- 12 downloads × 10 units = 120 units
Total: ~240 units/month

Well under free tier limits! 🎉
```

### If you exceed limits:

1. You'll get HTTP 429 errors
2. App has automatic retry with exponential backoff
3. Consider reducing search frequency
4. Check for bugs causing excessive API calls

## Troubleshooting

### "Error 403: Access Not Configured"

**Cause:** Gmail API not enabled for project

**Fix:**
```bash
# Go to: https://console.cloud.google.com/apis/library
# Search: Gmail API
# Click: Enable
```

### "Error 400: redirect_uri_mismatch"

**Cause:** OAuth client type is wrong

**Fix:** Delete credentials and recreate as **Desktop app** (not Web app)

### "Error 403: Project not verified"

**Cause:** You didn't add yourself as test user

**Fix:**
```bash
# Go to: https://console.cloud.google.com/apis/credentials/consent
# Click: Add Users
# Enter your Gmail address
```

### "Invalid Credentials" in oauth_setup.py

**Cause:** credentials.json is corrupted or wrong format

**Fix:**
```bash
# Re-download credentials.json from Google Cloud Console
# Verify it's valid JSON:
python -m json.tool credentials/credentials.json
```

### Browser doesn't open during OAuth

**Cause:** No default browser or display issues

**Fix:**
```bash
# Manual OAuth URL will be displayed
# Copy and paste into browser manually
# Complete OAuth flow
# Copy code back to terminal
```

## Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Gmail API Quotas](https://developers.google.com/gmail/api/reference/quota)
- [Google Cloud Console](https://console.cloud.google.com/)

## Common Questions

### Q: Do I need a billing account?

**A:** No! Gmail API is free for typical usage.

### Q: Can I use this for multiple Gmail accounts?

**A:** Yes, but you need separate OAuth tokens for each account. Run `oauth_setup.py` for each account with different credentials.

### Q: Will Google review my app?

**A:** No, as long as you stay in "Testing" mode with <100 users. Perfect for personal use.

### Q: Can I share my credentials.json with others?

**A:** No! Each person should create their own Google Cloud project and credentials.

### Q: How long does the OAuth token last?

**A:** Access tokens expire after 1 hour, but refresh tokens last indefinitely. The app automatically refreshes tokens as needed.

## Next Steps

After completing this setup:

1. ✅ Run OAuth setup: `uv run python scripts/oauth_setup.py`
2. ✅ Test Gmail access via Claude Desktop
3. ✅ Create your first schedule
4. ✅ Set up cron job (see CRON_SETUP.md)

---

**Need help?** Check the main [README.md](README.md) or open an issue on GitHub.
