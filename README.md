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
- `ATS_SHOPWARE_ACCESS_KEY_ID_TRUNK`: Shopware Admin API integration access key used by ATS for trunk.
- `ATS_SHOPWARE_SECRET_ACCESS_KEY_TRUNK`: Shopware Admin API integration secret used by ATS for trunk.
- `SLACK_WEBHOOK_URL`: optional Slack Incoming Webhook URL used to post nightly deployment status.

Variables:

- `SW_PAAS_PROJECT`: PaaS project name.
- `SW_PAAS_ORGANIZATION`: optional; defaults to `shopware-qa` when empty.
- `ATS_APP_URL_TRUNK`: public URL of the deployed trunk PaaS application.

Each ATS matrix target resolves its configuration through `ats_config_suffix`. The current
trunk target uses `TRUNK`, so future `paas/*` targets should add their own safe suffix and matching
`ATS_APP_URL_<SUFFIX>`, `ATS_SHOPWARE_ACCESS_KEY_ID_<SUFFIX>`, and
`ATS_SHOPWARE_SECRET_ACCESS_KEY_<SUFFIX>` entries.

ATS runs set `SHOPWARE_ACCEPTANCE_INSTANCE_TYPE=paas` so the upstream acceptance suite can
apply PaaS-specific behavior once it supports that signal.

## Workflow

The nightly workflow runs at `02:17 UTC`. It avoids minute `0` because GitHub Actions scheduled workflows are often delayed at the top of the hour.

For each target, the workflow:

1. Checks out the target PaaS branch.
2. Updates `shopware/platform` with Composer.
3. Commits and pushes `composer.lock` when it changed.
4. Updates the matching Shopware PaaS application.
5. Retries transient PaaS deployment failures up to three times.
6. Runs `shopware/shopware` ATS smoke coverage against the deployed URL.
7. Uploads Playwright `test-results` and `playwright-report` artifacts.
8. Posts deployment status to Slack when `SLACK_WEBHOOK_URL` is configured.

The current ATS smoke target is the trunk storefront search spec:
`tests/acceptance/tests/Search/ProductSearch.spec.ts`. It creates two basic products
through ATS, clears caches, and verifies that the deployed storefront can find the created
content through search suggestions and the search results page.
