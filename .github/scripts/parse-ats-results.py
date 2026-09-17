#!/usr/bin/env python3
"""
Parse Playwright test results from test-results.json artifacts and extract failed/flaky tests.
"""

import json
import sys
from pathlib import Path
from typing import Optional

def load_test_results(results_file: Path) -> dict:
    """Load test results from test-results.json"""
    if not results_file.exists():
        return {"tests": []}
    
    try:
        with open(results_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Failed to load {results_file}: {e}", file=sys.stderr)
        return {"tests": []}

def extract_test_info(test: dict) -> dict:
    """Extract relevant test information"""
    location = test.get("location", "")
    title = test.get("title", "Unknown test")
    
    return {
        "title": title,
        "location": location,
        "status": test.get("status", "unknown"),
        "flaky": test.get("flaky", False),
    }

def process_results(artifact_dirs: list) -> tuple:
    """Process test results from all artifact directories and return failed and flaky tests"""
    all_tests = []
    
    for artifact_dir in artifact_dirs:
        artifact_dir = Path(artifact_dir)
        if not artifact_dir.exists():
            continue
        
        # Find test-results.json in the artifact directory
        test_results_file = artifact_dir / "shopware" / "tests" / "acceptance" / "test-results" / "test-results.json"
        if not test_results_file.exists():
            # Try alternate path
            test_results_file = artifact_dir / "test-results.json"
        
        if test_results_file.exists():
            results = load_test_results(test_results_file)
            for test in results.get("tests", []):
                all_tests.append(extract_test_info(test))
    
    # Separate failed and flaky tests
    failed_tests = [t for t in all_tests if t["status"] == "failed"]
    flaky_tests = [t for t in all_tests if t["flaky"] and t["status"] != "failed"]
    
    return failed_tests, flaky_tests, len(all_tests)

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
            location = test["location"].split(":")[0] if test["location"] else "unknown"
            lines.append(f"  • {location} › {test['title']}")
        lines.append("")
    
    if flaky_tests:
        lines.append(f"*⚠️  Flaky Tests ({len(flaky_tests)}):*")
        for test in flaky_tests:
            location = test["location"].split(":")[0] if test["location"] else "unknown"
            lines.append(f"  • {location} › {test['title']}")
        lines.append("")
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Usage: parse-ats-results.py <artifact_dir1> [artifact_dir2] ...")
        sys.exit(1)
    
    artifact_dirs = sys.argv[1:]
    failed_tests, flaky_tests, total_tests = process_results(artifact_dirs)
    
    message = format_slack_message(failed_tests, flaky_tests)
    
    if message:
        print(message)
    else:
        print("No failed or flaky tests found.")

if __name__ == "__main__":
    main()
