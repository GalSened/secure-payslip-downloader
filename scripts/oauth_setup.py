#!/usr/bin/env python3
"""
OAuth Setup Script for Secure Payslip Downloader

This script guides you through the Gmail OAuth authentication process.
Run this script once to authenticate and save credentials for automated access.

Usage:
    uv run python scripts/oauth_setup.py

Requirements:
    1. Download credentials.json from Google Cloud Console
    2. Place credentials.json in: credentials/credentials.json
    3. Run this script and follow browser instructions
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from gmail_client import GmailClient, GmailAuthError
from config import get_config, get_logger
from security import verify_secure_permissions

logger = get_logger(__name__)


def print_header():
    """Print welcome message."""
    print("\n" + "=" * 70)
    print("  Secure Payslip Downloader - OAuth Setup")
    print("=" * 70)
    print("\nThis script will authenticate your Gmail account for automated payslip")
    print("downloads. You'll be redirected to your browser to authorize access.\n")


def print_instructions():
    """Print setup instructions."""
    print("BEFORE YOU BEGIN:")
    print("-" * 70)
    print("1. Create a Google Cloud project")
    print("2. Enable Gmail API")
    print("3. Create OAuth 2.0 credentials (Desktop app)")
    print("4. Download credentials.json")
    print("5. Place credentials.json in: credentials/credentials.json")
    print("-" * 70)
    print("\nFor detailed instructions, see: docs/google_cloud_setup.md")
    print()


def verify_credentials_exist(config) -> bool:
    """
    Verify that credentials.json exists.

    Args:
        config: Configuration object

    Returns:
        True if credentials exist, False otherwise
    """
    if not config.gmail_creds_path.exists():
        print(f"❌ ERROR: credentials.json not found!")
        print(f"   Expected location: {config.gmail_creds_path}")
        print(f"\n   Please:")
        print(f"   1. Download credentials.json from Google Cloud Console")
        print(f"   2. Save it to: {config.gmail_creds_path}")
        print(f"   3. Run this script again\n")
        return False

    print(f"✓ Found credentials.json at: {config.gmail_creds_path}")

    # Check permissions
    if not verify_secure_permissions(config.gmail_creds_path):
        print(f"   ⚠️  Warning: credentials.json has insecure permissions!")
        print(f"   Run: chmod 600 {config.gmail_creds_path}")

    return True


def run_oauth_flow(client: GmailClient) -> bool:
    """
    Run OAuth authentication flow.

    Args:
        client: GmailClient instance

    Returns:
        True if authentication succeeded, False otherwise
    """
    print("\n" + "=" * 70)
    print("STARTING OAUTH AUTHENTICATION")
    print("=" * 70)
    print("\nA browser window will open for authentication.")
    print("Please:")
    print("  1. Sign in with your Gmail account")
    print("  2. Review the permissions (read-only access)")
    print("  3. Click 'Allow' to grant access")
    print("  4. Close the browser when authentication completes")
    print("\nPress Ctrl+C to cancel at any time.")
    print("-" * 70)

    try:
        # Run authentication
        creds = client.authenticate()

        if creds and creds.valid:
            print("\n✓ Authentication successful!")
            print(f"✓ Token saved to: {client.token_path}")

            # Verify token permissions
            if verify_secure_permissions(client.token_path):
                print("✓ Token has secure permissions (0600)")
            else:
                print("⚠️  Warning: Token has insecure permissions!")

            return True
        else:
            print("\n❌ Authentication failed: Invalid credentials")
            return False

    except GmailAuthError as e:
        print(f"\n❌ Authentication failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n\n⚠️  Authentication cancelled by user")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        logger.exception("OAuth setup failed")
        return False


def test_api_access(client: GmailClient) -> bool:
    """
    Test that Gmail API access works.

    Args:
        client: GmailClient instance

    Returns:
        True if API access works, False otherwise
    """
    print("\n" + "=" * 70)
    print("TESTING GMAIL API ACCESS")
    print("=" * 70)

    try:
        service = client.get_service()

        # Simple API call to verify access
        profile = service.users().getProfile(userId='me').execute()
        email = profile.get('emailAddress', 'Unknown')

        print(f"\n✓ Gmail API access working!")
        print(f"✓ Authenticated account: {email}")
        print(f"✓ Messages in mailbox: {profile.get('messagesTotal', 'Unknown')}")

        return True

    except Exception as e:
        print(f"\n❌ API test failed: {e}")
        logger.exception("API test failed")
        return False


def print_next_steps():
    """Print next steps after successful setup."""
    print("\n" + "=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print("\nYou can now:")
    print("  1. Use the MCP tools to search and download payslips")
    print("  2. Create scheduled downloads with create_monthly_schedule")
    print("  3. Let the cron job handle automatic downloads")
    print("\nYour authentication token is stored securely in:")
    print("  credentials/token.pickle")
    print("\n⚠️  IMPORTANT:")
    print("  - Keep credentials/ directory secure (permissions: 0700)")
    print("  - Never commit credentials/ to git (already in .gitignore)")
    print("  - Token is encrypted and only readable by your user account")
    print("\nFor usage examples, see: README.md")
    print("=" * 70 + "\n")


def main():
    """Main OAuth setup flow."""
    print_header()
    print_instructions()

    # Get configuration
    try:
        config = get_config()
        print(f"✓ Configuration loaded")
        print(f"  Project root: {config.project_root}")
        print(f"  Download path: {config.download_base_path}")
        print(f"  Timezone: {config.timezone}")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)

    # Verify credentials.json exists
    if not verify_credentials_exist(config):
        sys.exit(1)

    # Create Gmail client
    client = GmailClient()

    # Check if already authenticated
    if client.token_path.exists():
        print(f"\n⚠️  Found existing token at: {client.token_path}")
        response = input("Do you want to re-authenticate? (y/N): ").strip().lower()
        if response != 'y':
            print("\nKeeping existing token. Testing API access...")
            if test_api_access(client):
                print_next_steps()
                sys.exit(0)
            else:
                print("\nExisting token doesn't work. Re-authenticating...")
                # Delete bad token
                try:
                    client.token_path.unlink()
                except Exception as e:
                    print(f"Failed to delete bad token: {e}")

    # Run OAuth flow
    print()
    input("Press Enter to start OAuth authentication...")

    if not run_oauth_flow(client):
        print("\n❌ Setup failed. Please try again or check the logs.")
        sys.exit(1)

    # Test API access
    if not test_api_access(client):
        print("\n❌ Setup incomplete. Authentication succeeded but API test failed.")
        sys.exit(1)

    # Success!
    print_next_steps()
    sys.exit(0)


if __name__ == '__main__':
    main()
