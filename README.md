# nightly-paas-ats

Nightly Shopware PaaS deployments for trunk and maintained branches, used to run ATS acceptance tests against real PaaS environments.

## Purpose

This repository owns the official Redstone automation for validating Shopware on Shopware PaaS before the result is consumed by acceptance tests.

The workflow is intentionally split from `shopware/shopware`: this repo manages PaaS application roots, deployment automation, and test orchestration, while the tested source still comes from `shopware/shopware` through Composer.

## Repository Layout

- `main`: orchestration, workflows, and documentation.
- `paas/trunk`: root-level PaaS application for `shopware/platform: dev-trunk`.
- `paas/6.6.x`: root-level PaaS application for the maintained Shopware 6.6 branch.

PaaS application branches are separate because Shopware PaaS builds from the repository root at a commit SHA. Keeping each target in its own branch lets each branch carry its own `composer.json`, `composer.lock`, and `.shopware-project.yaml` without mixing version-specific files.

## Current Targets

| Target | Branch | PaaS application | Composer constraint |
| --- | --- | --- | --- |
| trunk | `paas/trunk` | `nightly-ats-trunk` | `dev-trunk` |
| 6.6.x | `paas/6.6.x` | `nightly-ats-66x` | `6.6.x-dev` |

## Required GitHub Configuration

Secrets:

- `SW_PAAS_TOKEN`: Shopware PaaS token used by the workflow to update and deploy the application. Use a service-account token for CI/CD automation.
- `COMPOSER_UPDATE_TOKEN`: optional PAT used for pushing lock-file updates. If it is not configured, the workflow falls back to `GITHUB_TOKEN`.
- `ATS_SHOPWARE_ACCESS_KEY_ID_TRUNK`: Shopware Admin API integration access key used by ATS for trunk.
- `ATS_SHOPWARE_SECRET_ACCESS_KEY_TRUNK`: Shopware Admin API integration secret used by ATS for trunk.
- `ATS_SHOPWARE_ACCESS_KEY_ID_V66`: Shopware Admin API integration access key used by ATS for 6.6.x.
- `ATS_SHOPWARE_SECRET_ACCESS_KEY_V66`: Shopware Admin API integration secret used by ATS for 6.6.x.
- `SLACK_WEBHOOK_URL`: Slack Incoming Webhook URL used to post nightly deployment and ATS status.

Shopware PaaS Native authentication moved to Shopware Account in July 2026. Personal access tokens tied to migrated user accounts can become invalid; keep this workflow on a current `sw-paas` CLI release and prefer a long-lived service-account token for `SW_PAAS_TOKEN`.
The pinned `sw-paas` CLI version and Linux x86_64 checksum live in `.github/sw-paas-cli.env`.

Variables:

- `SW_PAAS_ORGANIZATION_ID`: PaaS organization ID used to create the CLI context file for service-account tokens.
- `SW_PAAS_PROJECT_ID`: PaaS project ID used to create the CLI context file for service-account tokens.
- `ATS_APP_URL_TRUNK`: public URL of the deployed trunk PaaS application.
- `ATS_APP_URL_V66`: public URL of the deployed 6.6.x PaaS application.

Each ATS target resolves its configuration through `ats_config_suffix`: trunk uses `TRUNK` and
6.6.x uses `V66`. Future `paas/*` targets should add their own safe suffix and matching
`ATS_APP_URL_<SUFFIX>`, `ATS_SHOPWARE_ACCESS_KEY_ID_<SUFFIX>`, and
`ATS_SHOPWARE_SECRET_ACCESS_KEY_<SUFFIX>` entries.

ATS runs set `SHOPWARE_ACCEPTANCE_INSTANCE_TYPE=paas` so the upstream acceptance suite can
apply PaaS-specific behavior once it supports that signal.

## Workflow

The nightly workflow runs at `02:17 UTC`. It avoids minute `0` because GitHub Actions scheduled workflows are often delayed at the top of the hour.

One control-plane run starts trunk and 6.6.x independently at the same time. A deployment or ATS
failure for one target does not suppress the other target's jobs, artifacts, or status. The final
Slack message combines both results. Manual runs can select `all`, `trunk`, or `6.6.x` and can force
deployment even when a target's `composer.lock` did not change.

For each selected target, the reusable target workflow:

1. Checks out the target PaaS branch.
2. Updates `shopware/platform` with Composer.
3. Commits and pushes `composer.lock` when it changed.
4. Updates the matching Shopware PaaS application.
5. Retries transient PaaS deployment failures up to three times.
6. Runs the full `shopware/shopware` ATS `Platform` project against the deployed URL.
7. Splits the Platform project into two Playwright shards to reduce wall-clock runtime.
8. Uploads target-specific Playwright `test-results` and `playwright-report` artifacts for each shard.
   Failed tests retain traces, screenshots, and videos; artifacts are kept for seven days.
9. Returns a target summary to the control-plane workflow, which posts one combined Slack status.

The ATS Platform suite runs:
`npx playwright test --config=playwright.paas.config.ts --workers=1 --project=Platform --shard=<shard>/2`.

Each target keeps its deployment and ATS jobs in the same reusable workflow so ATS directly depends
on the matching deployment. The root workflow calls that reusable workflow once per selected target
and owns the combined notification. Install, update, and other non-Platform projects are not part of
this workflow yet.

## Maintenance

The `Shopware PaaS CLI Update Check` workflow runs weekly and can also be triggered manually.
It checks the latest `shopware/sw-paas` GitHub release against the pinned
`SW_PAAS_CLI_VERSION` in `.github/sw-paas-cli.env`. When a newer release is
available, it updates the pinned version and Linux x86_64 checksum, then opens or updates a
pull request for review.
