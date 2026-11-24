# GitHub Branch Protection & Repository Security Governance Policy

## 1. Objective & Scope

This specification defines the mandatory branch protection rules and automated governance policies enforced for the **EduAtlas / ScholarPilot AI** production repository.

All direct commits to `main` (and `master`) are strictly prohibited. Every change must be delivered via an authenticated, peer-reviewed Pull Request (PR) that passes 100% of the automated CI/CD quality and security gates.

---

## 2. Mandatory Branch Protection Rules (Target: `main`, `master`)

In accordance with DevSecOps zero-trust principles, the repository configuration in GitHub Settings -> Branches must enforce the following rules:

### A. Require a Pull Request Before Merging
- **Require approvals:** Minimum of **1 approving review** from a designated code owner or senior engineer before any PR can be merged.
- **Dismiss stale pull request approvals when new commits are pushed:** `ENABLED` (prevents malicious/accidental commits after an initial approval).
- **Require review from Code Owners (`CODEOWNERS`):** `ENABLED`.
- **Restrict who can dismiss pull request reviews:** Restricted strictly to repository administrators.

### B. Require Status Checks to Pass Before Merging
- **Require branches to be up to date before merging:** `ENABLED` (Strict merge queue / rebase-merge pattern).
- **Mandatory Passing Status Checks:**
  1. `Lint & Code Style (Ruff)` (from `.github/workflows/ci.yml`)
  2. `Static Type Check (Mypy)` (from `.github/workflows/ci.yml`)
  3. `Dependency Security Audit (pip-audit)` (from `.github/workflows/ci.yml`)
  4. `Python Test Suite & Coverage` (from `.github/workflows/ci.yml`)
  5. `Repository Policy & Security Gates Verification` (from `.github/workflows/repository-policy.yml`)
  6. `Vulnerability & Secret Scan` (from `.github/workflows/security-scan.yml`)

### C. Require Conversation Resolution Before Merging
- All review comments and discussion threads must be resolved before a PR can be merged.

### D. Require Signed Commits (GPG / SSH / S/MIME)
- **Require signed commits:** `ENABLED`. Commits without a verified cryptographic signature are rejected at the remote gate.

### E. Block Dangerous Git Operations
- **Do not allow bypassing the above settings:** `ENABLED` (Enforce rules on administrators).
- **Allow force pushes:** `DISABLED` (`git push --force` or `--force-with-lease` rejected).
- **Allow deletions:** `DISABLED` (Branch deletion of `main` / `master` blocked).

---

## 3. GitHub REST API / CLI Ruleset Configuration

Administrators can verify or apply these branch protection rules using the GitHub CLI (`gh`):

```bash
# Apply branch protection rule via GitHub CLI
gh api -X PUT /repos/:owner/:repo/branches/main/protection \
  -H "Accept: application/vnd.github.v3+json" \
  -F "required_status_checks[strict]=true" \
  -F "required_status_checks[contexts][]=Lint & Code Style (Ruff)" \
  -F "required_status_checks[contexts][]=Static Type Check (Mypy)" \
  -F "required_status_checks[contexts][]=Dependency Security Audit (pip-audit)" \
  -F "required_status_checks[contexts][]=Python Test Suite & Coverage" \
  -F "required_status_checks[contexts][]=Repository Policy & Security Gates Verification" \
  -F "enforce_admins=true" \
  -F "required_pull_request_reviews[dismiss_stale_reviews]=true" \
  -F "required_pull_request_reviews[require_code_owner_reviews]=true" \
  -F "required_pull_request_reviews[required_approving_review_count]=1" \
  -F "restrictions=null" \
  -F "allow_force_pushes=false" \
  -F "allow_deletions=false" \
  -F "required_conversation_resolution=true"
```

---

## 4. Automated Verification via CI (`repository-policy.yml`)

To prevent repository configuration drift or manual misconfiguration, `.github/workflows/repository-policy.yml` runs on every push and PR:
1. Validates that all required security and deployment workflows exist (`ci.yml`, `deploy.yml`, `security-scan.yml`, `repository-policy.yml`).
2. Validates that the deployment workflow strictly requires successful completion of all upstream CI gates (`lint`, `typecheck`, `security-audit`, `test`).
3. Validates that dependency vulnerability scanners (`pip-audit`, `npm audit`) are wired into CI.
4. Fails the build immediately if any security gate or policy contract is omitted.
