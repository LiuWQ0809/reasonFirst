## Purpose

Related issue and the problem addressed. Keep the PR focused.

## Changes and compatibility

Describe user-facing behavior, documentation, CLI/state compatibility and non-goals. State whether this changes security boundaries, dependencies, credentials, or local/remote writes.

## Verification actually performed

Commands, results, platforms and exact tested SHA. Distinguish local tests, CI, synthetic fixtures and live-service tests. List skipped or untested cases; do not claim a docs-only CI job is a full application build.

## Review checklist

- [ ] I reviewed the implementation and have permission to submit the contribution, including any AI-assisted material.
- [ ] Relevant regression coverage and current docs/Unreleased notes are included.
- [ ] No secrets, private endpoints/data, raw unreviewed logs, credentials or migration backups are attached or committed.
- [ ] No unsupported sandbox/atomicity/coverage claims or silent permission expansion were introduced.
- [ ] I did not weaken tests/scanners to obtain green CI.

A green check is not merge authorization. Release tags, package publication, deployment and visibility changes require separate approval.
