# nightly-paas-ats

Nightly Shopware PaaS deployments for trunk and maintained branches, used to run ATS acceptance tests against real PaaS environments.

## Purpose

This repository owns the official Redstone automation for validating Shopware on Shopware PaaS before the result is consumed by acceptance tests.

The workflow is intentionally split from `shopware/shopware`: this repo manages PaaS application roots, deployment automation, and test orchestration, while the tested source still comes from `shopware/shopware` through Composer.

## Repository Layout

- `main`: orchestration, workflows, and documentation.
- `paas/trunk`: root-level PaaS application for `shopware/platform: dev-trunk`.
- `paas/6.6.x`: planned root-level PaaS application for the maintained 6.6 branch.

PaaS application branches are separate because Shopware PaaS builds from the repository root at a commit SHA. Keeping each target in its own branch lets each branch carry its own `composer.json`, `composer.lock`, and `.shopware-project.yaml` without mixing version-specific files.

## Current Target

| Target | Branch | PaaS application | Composer constraint |
| --- | --- | --- | --- |
| trunk | `paas/trunk` | `nightly-ats-trunk` | `dev-trunk` |

## Required GitHub Configuration

Secrets:

- `SW_PAAS_TOKEN`: PaaS token used by the workflow to update and deploy the application.
- `COMPOSER_UPDATE_TOKEN`: optional PAT used for pushing lock-file updates. If it is not configured, the workflow falls back to `GITHUB_TOKEN`.

Variables:

- `SW_PAAS_PROJECT`: PaaS project name.
- `SW_PAAS_ORGANIZATION`: optional; defaults to `shopware-qa` when empty.

## Workflow

The nightly workflow runs at `02:17 UTC`. It avoids minute `0` because GitHub Actions scheduled workflows are often delayed at the top of the hour.

For each target, the workflow:

1. Checks out the target PaaS branch.
2. Updates `shopware/platform` with Composer.
3. Commits and pushes `composer.lock` when it changed.
4. Updates the matching Shopware PaaS application.
5. Retries transient PaaS deployment failures up to three times.

ATS execution will be added after the trunk PaaS target is stable in this repository.
