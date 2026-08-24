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

`main`, `paas/trunk`, and `paas/6.6.x` are protected from deletion by a repository ruleset. All other branches are deleted automatically once their pull request is merged (see [`docs/branch-layout.md`](docs/branch-layout.md)).

## Current Target

| Target | Branch | PaaS application | Composer constraint |
| --- | --- | --- | --- |
| trunk | `paas/trunk` | `nightly-ats-trunk` | `dev-trunk` |

## Required GitHub Configuration

Secrets:

- `SW_PAAS_TOKEN`: Shopware PaaS token used by the workflow to update and deploy the application. Use a service-account token for CI/CD automation.
- `COMPOSER_UPDATE_TOKEN`: optional PAT used for pushing lock-file updates. If it is not configured, the workflow falls back to `GITHUB_TOKEN`.
- `ATS_SHOPWARE_ACCESS_KEY_ID_TRUNK`: Shopware Admin API integration access key used by ATS for trunk.
- `ATS_SHOPWARE_SECRET_ACCESS_KEY_TRUNK`: Shopware Admin API integration secret used by ATS for trunk.
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL used to post nightly deployment and ATS status.

Shopware PaaS Native authentication moved to Shopware Account in July 2026. Personal access tokens tied to migrated user accounts can become invalid; keep this workflow on a current `sw-paas` CLI release and prefer a long-lived service-account token for `SW_PAAS_TOKEN`.
The pinned `sw-paas` CLI version and Linux x86_64 checksum live in `.github/sw-paas-cli.env`.

Variables:

- `SW_PAAS_ORGANIZATION_ID`: PaaS organization ID used to create the CLI context file for service-account tokens.
- `SW_PAAS_PROJECT_ID`: PaaS project ID used to create the CLI context file for service-account tokens.
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
6. Runs the full `shopware/shopware` ATS `Platform` project against the deployed URL.
7. Splits the Platform project into two Playwright shards to reduce wall-clock runtime.
8. Uploads Playwright `test-results` and `playwright-report` artifacts for each shard.
9. Posts combined deployment and ATS status to Slack when `SLACK_WEBHOOK_URL` is configured.

The ATS Platform suite runs:
`npx playwright test --workers=1 --project=Platform --shard=<shard>/2`.

The deployment and ATS jobs stay in the same workflow so ATS can directly depend on the
deployment job and the final Slack notification can summarize both phases without a
cross-workflow handoff. Install, update, and other non-Platform projects are not part of
this workflow yet.

## Maintenance

The `Shopware PaaS CLI Update Check` workflow runs weekly and can also be triggered manually.
It checks the latest `shopware/sw-paas` GitHub release against the pinned
`SW_PAAS_CLI_VERSION` in `.github/sw-paas-cli.env`. When a newer release is
available, it updates the pinned version and Linux x86_64 checksum, then opens or updates a
pull request for review.
