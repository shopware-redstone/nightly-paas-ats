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
    
    lines = log_text.split('\n')
    current_section = None
    
    for line in lines:
        # Look for section headers like "  3 failed" or "  2 flaky"
        if re.search(r'^\s+\d+\s+failed', line):
            current_section = 'failed'
            continue
        elif re.search(r'^\s+\d+\s+flaky', line):
            current_section = 'flaky'
            continue
        elif re.search(r'^\s+\d+\s+(skipped|passed)', line):
            current_section = None
            continue
        
        # Parse test entries (indented lines with test paths)
        if current_section and line.startswith('    '):
            test_entry = line.strip()
            if test_entry.startswith('[Platform]'):
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
            lines.append(f"  • {test}")
        lines.append("")
    
    if flaky_tests:
        lines.append(f"*⚠️  Flaky Tests ({len(flaky_tests)}):*")
        for test in flaky_tests:
            lines.append(f"  • {test}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: parse-ats-results.py <log_text>")
        print("Reads Playwright test output from stdin or as argument")
        sys.exit(1)
    
    # Read from stdin or from argument
    if sys.argv[1] == '-':
        log_text = sys.stdin.read()
    else:
        log_text = sys.argv[1]
    
    failed_tests, flaky_tests = parse_playwright_output(log_text)
    message = format_slack_message(failed_tests, flaky_tests)
    
    if message:
        print(message)

if __name__ == "__main__":
    main()
