# Engineering Policy

These policies govern day-to-day engineering operations. Violations are reviewed
in the next retrospective.

## 1. Git Branching

The repository uses a long-lived branch model with two protected branches.

- `main` — always production-ready. Every commit on `main` is deployable.
- `develop` — integration branch where feature branches are merged before release.
- `feature/<ticket-id>-<short-description>` — branched from `develop`,
  one feature per branch, rebased onto `develop` before merge.
- `hotfix/<ticket-id>-<short-description>` — branched from `main`, used for
  production fixes that cannot wait for the next release cycle.
- `release/vX.Y.Z` — branched from `develop` when cutting a release. Only
  bug fixes go onto a release branch; new features wait for the next cycle.

## 2. Hotfix Policy

- A hotfix is **always branched from `main`**, never from `develop`.
- After merge to `main`, the same fix must be **merged back into `develop`** to
  prevent regression in the next release.
- Hotfixes require **one approval minimum** (expedited review) and must include
  an automated test reproducing the bug.
- A hotfix must be **deployed within 2 hours** of merging to `main`. If the
  deployment cannot happen in that window, the merge is reverted.

## 3. Code Review Policy

- **Two approvals** are required for merge to `develop` or `main`.
- The author cannot approve their own pull request.
- Reviewers must **run non-trivial changes locally** before approving.
  "Looks good" without execution is not an approval.
- **All review comments must be resolved** before merge. The author resolves
  by either fixing or replying with rationale; the reviewer marks the thread done.
- Review SLA: first response within one business day.

## 4. Secrets Management

- **Never commit credentials** to any branch ever. This includes development,
  feature, and abandoned branches. A leaked secret on any branch is treated as
  if it were leaked on `main`.
- Local development uses a `.env` file that is **always gitignored**.
- Production secrets live in **HashiCorp Vault** (or **GCP Secret Manager** for
  GCP-hosted services). Applications fetch secrets at startup, never read them
  from disk in production.
- Secrets are **rotated quarterly** and immediately on personnel changes.

## 5. Dependency Policy

- Dependencies undergo a **quarterly audit** for known CVEs.
- Packages with **unpatched CVEs of severity High or Critical** are blocked
  at the artifact registry and cannot be installed.
- Production lockfiles **pin exact versions** (`==1.2.3`). Range specifiers
  (`>=1.2.3`) are allowed only in development dependencies.
- **Dependabot** raises automated PRs for updates. Security patches are
  reviewed and merged within 7 days; routine updates within 30 days.

## 6. Incident Classification

- **SEV1** — full outage of a customer-facing service. Page oncall **immediately**.
  Customer communication required within 30 minutes.
- **SEV2** — partial degradation: a region is down, a major feature is broken,
  or latency is 10× normal. Page oncall **within 15 minutes**.
- **SEV3** — minor user-visible bug, workaround exists. Filed as a regular
  ticket the next business day.
- **SEV1 and SEV2 incidents require a postmortem within 48 hours**, written
  blameless, with action items assigned and tracked to completion.

## 7. Deployment Policy

- Deployments happen **only during business hours** (Mon-Thu, 09:00-16:00 local).
  Hotfixes are the only exception.
- Every deployment requires **green CI**: unit tests, integration tests,
  and security scans all pass.
- **Staged rollout** is mandatory for any service with more than 100 active users:
  10% of traffic → 50% → 100%, with at least 30 minutes of observation between stages.
- Every deployment has a **documented rollback plan** in the change ticket.
  The plan must be runnable by oncall without consulting the author.

## 8. Documentation Standard

- **Every service has a README** containing: setup instructions, architecture
  overview, list of dependencies, and a runbook for common incidents.
- **Architecture Decision Records (ADRs)** are required for any choice that
  affects more than one service or that locks the team into a vendor.
  ADRs live in `docs/adr/` next to the code.
- Documentation lives **in the same repository as the code**. External wikis
  go stale; in-repo docs go through code review with the change.
- Every public function in a library package has a docstring. Public APIs are
  additionally documented in the service README with usage examples.
