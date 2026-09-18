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
        root / "shopware" / "tests" / "acceptance" / "test-results" / "test-results.json",
    ]
    return [candidate for candidate in candidates if candidate.exists()]


def iter_specs(suite: dict):
    """Yield Playwright spec entries from the nested JSON report structure."""
    if not isinstance(suite, dict):
        return

    for child_suite in suite.get("suites") or []:
        if isinstance(child_suite, dict):
            yield from iter_specs(child_suite)

    for spec in suite.get("specs") or []:
        if isinstance(spec, dict):
            yield spec


def normalize_test(spec: dict, test: dict) -> Optional[dict]:
    """Normalize a Playwright test entry to a common shape used by the Slack formatter."""
    if not isinstance(test, dict):
        return None

    title = spec.get("title") or "Unknown test"
    location = spec.get("file", "")
    if not isinstance(location, str):
        location = ""

    results = test.get("results") or []
    statuses = []
    if isinstance(results, list):
        statuses = [result.get("status") for result in results if isinstance(result, dict)]

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

    return {
        "title": title,
        "location": str(location),
        "status": normalized_status,
        "flaky": flaky,
    }


def load_test_results(results_file: Path) -> list[dict]:
    """Load a Playwright JSON report and flatten all test cases from the nested structure."""
    try:
        with open(results_file, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: Failed to load {results_file}: {exc}", file=sys.stderr)
        return []

    tests = []
    seen = set()

    for suite in payload.get("suites") or []:
        if not isinstance(suite, dict):
            continue

        for spec in iter_specs(suite):
            for test in spec.get("tests") or []:
                normalized = normalize_test(spec, test)
                if normalized is None:
                    continue

                key = (normalized["title"], normalized["location"])
                if key in seen:
                    continue
                seen.add(key)
                tests.append(normalized)

    return tests


def process_results(artifact_dirs: list) -> tuple:
    """Process test results from all artifact directories and return failed and flaky tests."""
    all_tests = []

    for artifact_dir in artifact_dirs:
        artifact_dir = Path(artifact_dir)
        if not artifact_dir.exists():
            continue

        for test_results_file in find_result_files(artifact_dir):
            all_tests.extend(load_test_results(test_results_file))

    failed_tests = [test for test in all_tests if test["status"] == "failed"]
    flaky_tests = [test for test in all_tests if test["status"] == "flaky"]

    return failed_tests, flaky_tests, len(all_tests)


def format_slack_message(failed_tests: list, flaky_tests: list) -> Optional[str]:
    """Format test results for Slack message."""
    if not failed_tests and not flaky_tests:
        return None

    lines = [
        "*Test Results Details (from both shards):*",
        "",
    ]

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
    failed_tests, flaky_tests, _ = process_results(artifact_dirs)
    message = format_slack_message(failed_tests, flaky_tests)

    if message:
        print(message)


if __name__ == "__main__":
    main()
