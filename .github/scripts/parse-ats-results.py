#!/usr/bin/env python3
"""
Parse Playwright JSON results from artifacts and extract failed/flaky tests.
"""

import json
import sys
from pathlib import Path
from typing import Optional


def find_result_files(root: Path) -> list[Path]:
    """Return all discovered Playwright JSON report files under an artifact directory."""
    candidates = [
        root / "test-results" / "test-results.json",
        root / "test-results.json",  # Handle root-level placement
        root / "shopware" / "tests" / "acceptance" / "test-results" / "test-results.json",
    ]
    return [candidate for candidate in candidates if candidate.exists()]


def iter_specs(suite: dict, parent_file: str = "", parent_line: str = ""):
    """Yield (spec, file_path, line) tuples from nested JSON structure.

    Carries file path and line number from parent suite through to specs.
    """
    if not isinstance(suite, dict):
        return

    # Use suite's file if available, otherwise inherit from parent
    file_path = suite.get("file") or parent_file
    file_path = file_path if isinstance(file_path, str) else parent_file

    # Use suite's line if available, otherwise inherit from parent
    line = suite.get("line") or parent_line
    line = line if isinstance(line, (str, int)) else parent_line

    # Process child suites recursively
    for child_suite in suite.get("suites") or []:
        if isinstance(child_suite, dict):
            yield from iter_specs(child_suite, file_path, line)

    # Yield specs from this suite with inherited file path and line
    for spec in suite.get("specs") or []:
        if isinstance(spec, dict):
            yield spec, file_path, line


def normalize_test(spec: dict, file_path: str, line: str, test: dict) -> Optional[dict]:
    """Normalize a Playwright test entry to a common shape used by the Slack formatter.

    Uses full identity (file, title, line) from suite for accurate test deduplication.
    """
    if not isinstance(test, dict):
        return None

    title = spec.get("title") or "Unknown test"

    # Use the file path and line from parent suite (passed in), not from spec
    # Playwright stores these on the suite object, not on individual specs
    location = file_path if isinstance(file_path, str) else ""
    # Convert line to string if it's an int
    line = str(line) if line else ""

    # Check for expected failures: Playwright marks tests with expectedStatus: failed
    # These should not be reported as failures in Slack
    expected_status = test.get("expectedStatus")
    if expected_status == "failed":
        # This is an expected failure, skip reporting it
        return None

    results = test.get("results") or []
    statuses = []
    if isinstance(results, list):
        statuses = [result.get("status") for result in results if isinstance(result, dict)]

    # Use aggregate test.status as the authoritative status
    status = test.get("status")
    if not status and statuses:
        status = statuses[-1]

    if status == "flaky":
        normalized_status = "flaky"
    elif status == "unexpected":
        normalized_status = "failed"
    elif any(s in {"failed", "timedOut", "interrupted"} for s in statuses):
        normalized_status = "failed"
    elif status is None:
        normalized_status = "unknown"
    else:
        normalized_status = str(status)

    flaky = bool(test.get("flaky")) or any(
        isinstance(result, dict) and bool(result.get("flaky"))
        for result in results
    )

    if normalized_status == "unknown" and not flaky:
        return None

    # Use full identity (file:line:title) to prevent collapsing distinct tests
    return {
        "title": title,
        "location": location,
        "line": line,
        "status": normalized_status,
        "flaky": flaky,
        "identity": (location, title, line),  # Used for deduplication
    }


def load_test_results(results_file: Path) -> list[dict]:
    """Load a Playwright JSON report and flatten all test cases from the nested structure.

    Raises exceptions on parse failures to allow the workflow to detect incomplete results.
    """
    try:
        with open(results_file, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Error: Failed to load {results_file}: {exc}", file=sys.stderr)
        # Propagate the error so the workflow knows the report is invalid
        raise

    tests = []
    seen = set()

    for suite in payload.get("suites") or []:
        if not isinstance(suite, dict):
            continue

        for spec, file_path, line in iter_specs(suite):
            for test in spec.get("tests") or []:
                normalized = normalize_test(spec, file_path, line, test)
                if normalized is None:
                    continue

                # Use full identity (file, title, line) for deduplication
                # This prevents collapsing tests with same title but different files/lines
                key = normalized["identity"]
                if key in seen:
                    continue
                seen.add(key)
                tests.append(normalized)

    return tests


def process_results(artifact_dirs: list) -> tuple:
    """Process test results from all artifact directories and return failed and flaky tests.

    Applies cross-artifact de-duplication to prevent reporting the same test
    (e.g., shared setup failures) from multiple shards.

    Raises exceptions on parse failures so the workflow can detect incomplete results.
    """
    all_tests = []

    for artifact_dir in artifact_dirs:
        artifact_dir = Path(artifact_dir)
        if not artifact_dir.exists():
            continue

        for test_results_file in find_result_files(artifact_dir):
            try:
                all_tests.extend(load_test_results(test_results_file))
            except (json.JSONDecodeError, OSError) as exc:
                # Re-raise so the workflow knows this shard's results are invalid
                print(f"Error: Cannot process results from {artifact_dir}: {exc}", file=sys.stderr)
                raise

    # Apply cross-artifact de-duplication
    # Tests may appear in multiple shards (e.g., setup failures), so deduplicate
    # using the full identity tuple: (file, title, line)
    seen = set()
    deduplicated_tests = []
    for test in all_tests:
        key = test["identity"]
        if key not in seen:
            seen.add(key)
            deduplicated_tests.append(test)

    failed_tests = [test for test in deduplicated_tests if test["status"] == "failed"]
    flaky_tests = [test for test in deduplicated_tests if test["status"] == "flaky"]

    return failed_tests, flaky_tests, len(deduplicated_tests)


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
            location = test["location"] or "unknown"
            if test.get("line"):
                location = f"{location}:{test['line']}"
            lines.append(f"  • {location} › {test['title']}")
        lines.append("")

    if flaky_tests:
        lines.append(f"*⚠️  Flaky Tests ({len(flaky_tests)}):*")
        for test in flaky_tests:
            location = test["location"] or "unknown"
            if test.get("line"):
                location = f"{location}:{test['line']}"
            lines.append(f"  • {location} › {test['title']}")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: parse-ats-results.py <artifact_dir1> [artifact_dir2] ...")
        sys.exit(1)

    artifact_dirs = sys.argv[1:]
    try:
        failed_tests, flaky_tests, total_tests = process_results(artifact_dirs)
    except (json.JSONDecodeError, OSError) as exc:
        # Exit with error code so workflow knows results are incomplete
        print(f"Error: Failed to parse ATS results: {exc}", file=sys.stderr)
        sys.exit(1)

    message = format_slack_message(failed_tests, flaky_tests)

    if message:
        print(message)
    # Exit silently when no tests are found - prevents spurious Slack messages on successful runs


if __name__ == "__main__":
    main()