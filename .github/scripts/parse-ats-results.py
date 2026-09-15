#!/usr/bin/env python3
"""
Parse Playwright test output from job logs and extract failed/flaky tests.
Playwright outputs test results to stdout in a format like:
  3 failed
    [Platform] › tests/path.spec.ts:line › Test name › Additional info
  2 flaky
    [Platform] › tests/path.spec.ts:line › Test name
  2 skipped
  56 passed (16.7m)
"""

import re
import sys
from typing import Optional

def parse_playwright_output(log_text: str) -> tuple:
    """
    Parse Playwright test output and extract failed and flaky tests.
    Returns (failed_tests, flaky_tests)
    """
    failed_tests = []
    flaky_tests = []
    
    lines = log_text.splitlines()
    current_section = None
    
    for i, line in enumerate(lines):
        # Look for section headers like "  3 failed" or "  2 flaky"
        failed_match = re.search(r'^\s+(\d+)\s+failed', line)
        flaky_match = re.search(r'^\s+(\d+)\s+flaky', line)
        
        if failed_match:
            current_section = 'failed'
            continue
        elif flaky_match:
            current_section = 'flaky'
            continue
        elif re.search(r'^\s+\d+\s+(skipped|passed)', line):
            current_section = None
            continue
        
        # Parse test entries (indented lines with test paths)
        # Match lines that start with more indentation and contain test info
        if current_section and line.startswith('    ['):
            test_entry = line.strip()
            # Format: [Platform] › tests/path.spec.ts:line › Test name › Additional info
            if current_section == 'failed':
                failed_tests.append(test_entry)
            elif current_section == 'flaky':
                flaky_tests.append(test_entry)
    
    return failed_tests, flaky_tests

def format_slack_message(failed_tests: list, flaky_tests: list) -> Optional[str]:
    """Format test results for Slack message"""
    if not failed_tests and not flaky_tests:
        return None
    
    lines = []
    lines.append("*Test Results Details (from both shards):*")
    lines.append("")
    
    if failed_tests:
        lines.append(f"*❌ Failed Tests ({len(failed_tests)}):*")
        for test in failed_tests:
            # Format nicely: extract the file and test name
            lines.append(f"  • {test}")
        lines.append("")
    
    if flaky_tests:
        lines.append(f"*⚠️  Flaky Tests ({len(flaky_tests)}):*")
        for test in flaky_tests:
            lines.append(f"  • {test}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    # Read from argument or stdin
    if len(sys.argv) >= 2:
        if sys.argv[1] == '-':
            log_text = sys.stdin.read()
        else:
            with open(sys.argv[1], 'r') as f:
                log_text = f.read()
    else:
        if not sys.stdin.isatty():
            log_text = sys.stdin.read()
        else:
            print("Usage: parse-ats-results.py <log_file_or_->")
            print("Reads Playwright test output from file, stdin (when arg is '-'), or stdin (no args)")
            sys.exit(1)
    
    if not log_text.strip():
        sys.exit(0)
    
    failed_tests, flaky_tests = parse_playwright_output(log_text)
    message = format_slack_message(failed_tests, flaky_tests)
    
    if message:
        print(message)
    
    sys.exit(0)

if __name__ == "__main__":
    main()
