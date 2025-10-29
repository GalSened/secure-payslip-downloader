#!/usr/bin/env python3
"""
Setup automation script for Secure Payslip Downloader

This script helps you get started quickly by:
1. Verifying dependencies
2. Checking directory permissions
3. Validating configuration
4. Testing OAuth setup
5. Guiding you through first-time setup

Usage:
    uv run python scripts/setup.py
"""

import sys
import os
from pathlib import Path
import subprocess

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 70}{Colors.END}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠  {text}{Colors.END}")


def print_info(text: str):
    """Print info message."""
    print(f"  {text}")


def check_python_version() -> bool:
    """Check if Python version is 3.9+."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print_error(f"Python {version.major}.{version.minor}.{version.micro} (requires 3.9+)")
        return False


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print_success(f"uv {version}")
            return True
        else:
            print_error("uv not found")
            return False
    except FileNotFoundError:
        print_error("uv not installed")
        print_info("Install: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False


def check_directory_structure() -> bool:
    """Verify directory structure exists."""
    project_root = Path(__file__).parent.parent

    required_dirs = [
        'src',
        'scripts',
        'credentials',
        'schedules',
        'logs'
    ]

    all_exist = True
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            # Check permissions on sensitive directories
            if dir_name in ['credentials', 'schedules', 'logs']:
                mode = oct(dir_path.stat().st_mode)[-3:]
                if mode == '700':
                    print_success(f"Directory: {dir_name}/ (permissions: {mode})")
                else:
                    print_warning(f"Directory: {dir_name}/ (permissions: {mode}, should be 700)")
                    print_info(f"  Fix with: chmod 700 {dir_path}")
            else:
                print_success(f"Directory: {dir_name}/")
        else:
            print_error(f"Directory missing: {dir_name}/")
            all_exist = False

    return all_exist


def check_required_files() -> bool:
    """Check if required files exist."""
    project_root = Path(__file__).parent.parent

    required_files = [
        'src/server.py',
        'src/gmail_client.py',
        'src/scheduler.py',
        'src/config.py',
        'src/security.py',
        'scripts/oauth_setup.py',
        'scripts/run_scheduled_downloads.py',
        'README.md',
        'pyproject.toml'
    ]

    all_exist = True
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print_success(f"File: {file_path}")
        else:
            print_error(f"File missing: {file_path}")
            all_exist = False

    return all_exist


def check_credentials() -> tuple[bool, bool]:
    """Check credentials.json and token.pickle status."""
    project_root = Path(__file__).parent.parent
    creds_path = project_root / 'credentials' / 'credentials.json'
    token_path = project_root / 'credentials' / 'token.pickle'

    creds_exist = creds_path.exists()
    token_exist = token_path.exists()

    if creds_exist:
        mode = oct(creds_path.stat().st_mode)[-3:]
        if mode == '600':
            print_success("credentials.json exists (permissions: 600)")
        else:
            print_warning(f"credentials.json exists (permissions: {mode}, should be 600)")
            print_info(f"  Fix with: chmod 600 {creds_path}")
    else:
        print_warning("credentials.json not found")
        print_info("  Download from Google Cloud Console")
        print_info("  See: GOOGLE_CLOUD_SETUP.md")

    if token_exist:
        mode = oct(token_path.stat().st_mode)[-3:]
        if mode == '600':
            print_success("OAuth token exists (permissions: 600)")
        else:
            print_warning(f"OAuth token exists (permissions: {mode}, should be 600)")
            print_info(f"  Fix with: chmod 600 {token_path}")
    else:
        print_warning("OAuth token not found")
        print_info("  Run: uv run python scripts/oauth_setup.py")

    return creds_exist, token_exist


def check_schedules() -> bool:
    """Check if any schedules exist."""
    project_root = Path(__file__).parent.parent
    schedules_file = project_root / 'schedules' / 'tasks.json'

    if schedules_file.exists():
        import json
        try:
            with open(schedules_file, 'r') as f:
                schedules = json.load(f)
                count = len(schedules)
                if count > 0:
                    print_success(f"{count} schedule(s) configured")
                    return True
                else:
                    print_warning("No schedules configured")
                    print_info("  Use Claude Desktop to create schedules")
                    return False
        except:
            print_warning("schedules/tasks.json is corrupted")
            return False
    else:
        print_warning("No schedules file")
        print_info("  Will be created when you add first schedule")
        return False


def test_imports() -> bool:
    """Test if all modules can be imported."""
    modules = [
        'gmail_client',
        'scheduler',
        'config',
        'security',
        'server'
    ]

    all_import = True
    for module_name in modules:
        try:
            __import__(module_name)
            print_success(f"Module: {module_name}")
        except ImportError as e:
            print_error(f"Module: {module_name} - {e}")
            all_import = False

    return all_import


def print_next_steps(creds_exist: bool, token_exist: bool, has_schedules: bool):
    """Print next steps based on setup status."""
    print_header("NEXT STEPS")

    if not creds_exist:
        print("1️⃣  Get Google Cloud credentials:")
        print_info("   Follow: GOOGLE_CLOUD_SETUP.md")
        print_info("   Place credentials.json in: credentials/")
        print()

    if creds_exist and not token_exist:
        print("2️⃣  Complete OAuth authentication:")
        print_info("   Run: uv run python scripts/oauth_setup.py")
        print()

    if creds_exist and token_exist:
        print("3️⃣  Configure Claude Desktop:")
        print_info("   Edit: ~/Library/Application Support/Claude/claude_desktop_config.json")
        print_info("   See: claude_desktop_config_example.json")
        print()

        print("4️⃣  Create your first schedule:")
        print_info("   Use Claude Desktop with the MCP tools")
        print_info("   Tool: create_monthly_schedule")
        print()

        if has_schedules:
            print("5️⃣  Set up cron job:")
            print_info("   Run: crontab -e")
            print_info("   See: CRON_SETUP.md for details")
            print()

            print("6️⃣  Test automated download:")
            print_info("   Run: uv run python scripts/run_scheduled_downloads.py")
            print()


def main():
    """Run setup checks."""
    print()
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║      Secure Payslip Downloader - Setup Verification               ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    # Track overall status
    all_checks_pass = True

    # Check 1: Python version
    print_header("1. Python Version")
    if not check_python_version():
        all_checks_pass = False

    # Check 2: uv installation
    print_header("2. uv Package Manager")
    if not check_uv_installed():
        all_checks_pass = False

    # Check 3: Directory structure
    print_header("3. Directory Structure")
    if not check_directory_structure():
        all_checks_pass = False

    # Check 4: Required files
    print_header("4. Required Files")
    if not check_required_files():
        all_checks_pass = False

    # Check 5: Python modules
    print_header("5. Python Modules")
    if not test_imports():
        all_checks_pass = False
        print_warning("Run: uv sync")

    # Check 6: Credentials
    print_header("6. OAuth Credentials")
    creds_exist, token_exist = check_credentials()

    # Check 7: Schedules
    print_header("7. Scheduled Tasks")
    has_schedules = check_schedules()

    # Summary
    print_header("SETUP STATUS")

    if all_checks_pass and creds_exist and token_exist:
        print_success("All core components verified!")
        print()
        if has_schedules:
            print_success("Ready for automated downloads! 🎉")
        else:
            print_warning("Ready to create schedules")
        print()
    elif all_checks_pass and creds_exist:
        print_success("Almost there! Complete OAuth setup next.")
        print()
    elif all_checks_pass:
        print_success("Core components OK. Get credentials next.")
        print()
    else:
        print_error("Some checks failed. Fix issues above.")
        print()

    # Next steps
    print_next_steps(creds_exist, token_exist, has_schedules)

    # Footer
    print("=" * 70)
    print("Documentation:")
    print_info("README.md - Full usage guide")
    print_info("GOOGLE_CLOUD_SETUP.md - OAuth credential setup")
    print_info("CRON_SETUP.md - Automated scheduling guide")
    print("=" * 70)
    print()

    return 0 if all_checks_pass else 1


if __name__ == '__main__':
    sys.exit(main())
