# Branch Layout

This repository separates orchestration from PaaS application roots.

## `main`

`main` contains GitHub Actions workflows, documentation, and repo-level ownership files. It should not contain a Shopware application root.

## `paas/trunk`

`paas/trunk` contains the root-level Shopware PaaS project for nightly trunk validation.

Expected core files:

- `composer.json`
- `composer.lock`
- `.shopware-project.yaml`
- `bin/*`
- `config/*`
- `public/*`

The branch tracks `shopware/platform: dev-trunk`.

## `paas/6.6.x`

`paas/6.6.x` should be added after the trunk target is stable. It will use the same structure as `paas/trunk`, but with a 6.6-compatible Composer constraint and its own PaaS application.

## ATS

Acceptance tests should be run from `shopware/shopware` after a target deployment succeeds. The test runner should treat the PaaS URL as the system under test and upload Playwright/ATS artifacts for every nightly run.
