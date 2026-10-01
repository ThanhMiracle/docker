# GitHub Actions CI/CD for ACR and AKS

The application delivery flow uses GitHub Pull Requests as the authoritative
change record. It does not depend on Jira or another external ticketing system.

## Workflow boundaries

1. `pr-ci.yml` validates the PR change record, tests and coverage, frontend and
   container builds, SAST, dependency/secret/configuration scans, Helm rendering,
   and immutable-image policy.
2. `release.yml` accepts only a commit associated with an approved PR merged into
   `master`. It reruns the quality gate, builds the three release images once,
   smoke-tests those exact images, blocks on HIGH/CRITICAL image findings, pushes
   them to ACR, and records immutable digests.
3. The release workflow creates a CycloneDX SBOM and signed SLSA provenance for
   each image. `release-evidence` contains those files, coverage, PR metadata,
   a release manifest, and checksums.
4. `deploy-prod.yml` verifies the selected Build Release run and every evidence
   checksum, waits at the protected `production` environment, uses Azure OIDC,
   and deploys only the recorded digests.
5. `rollback-prod.yml` requires a human reason and protected-environment approval,
   verifies that the selected Helm revision contains the chosen release digests,
   restores it, and repeats verification.

Production verification failure never triggers an automatic rollback. The
workflow captures diagnostics and leaves rollback, recovery, pause, or
roll-forward to an authorized person.

## Required repository rules

Configure a ruleset for `master`:

- Require a pull request before merging.
- Require at least one approval and dismiss stale approvals.
- Require conversation resolution.
- Require `PR CI / Quality Gate`.
- Require approval from CODEOWNERS after `.github/CODEOWNERS` is populated with
  the real application and platform teams.
- Block force pushes and branch deletion.
- Do not allow bypass except through an audited break-glass process.

The release workflow also fails if a `master` commit is not associated with an
approved, merged PR. This is defense in depth and is not a replacement for the
repository ruleset.

## Required production environment protection

Create or update the GitHub Environment named `production`:

- Add one or more authorized required reviewers. Reviewers should be independent
  from the person initiating the deployment when separation of duties is required.
- Enable prevention of self-review.
- Restrict deployment branches to protected branches, or explicitly to `master`.
- Store production-only variables and secrets in this environment.

Both deploy and rollback jobs reference this environment. Without these settings,
the YAML alone cannot provide human production approval.

## Repository variables

| Variable | Purpose |
|---|---|
| `ACR_NAME` | ACR name without `.azurecr.io` |
| `ACR_LOGIN_SERVER` | For example `myacr.azurecr.io` |
| `AZURE_BUILD_CLIENT_ID` | OIDC identity that can push only to the application ACR |
| `AZURE_TENANT_ID` | Microsoft Entra tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID |

## Production environment variables and secrets

Variables:

| Variable | Purpose |
|---|---|
| `AZURE_DEPLOY_CLIENT_ID` | OIDC identity used only for AKS deployment |
| `AKS_RESOURCE_GROUP` | AKS resource group |
| `AKS_NAME` | AKS cluster name |
| `K8S_NAMESPACE` | Existing target namespace; defaults to `platform` |
| `INTERNAL_SMOKE_URL` | In-cluster Nginx URL; defaults to `http://nginx` |
| `PROD_SMOKE_TEST_URL` | Optional public HTTPS URL |
| `KEY_VAULT_ENABLED` | `true` or `false` |
| `KEY_VAULT_NAME` | Required when Key Vault is enabled |
| `API_KEYVAULT_CLIENT_ID` | API workload identity client ID |

Environment secrets:

- `DATABASE_URL` when Key Vault is disabled.
- `JWT_SECRET`, `ADMIN_EMAIL`.
- `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`.
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.
- Optional `ALERT_WEBHOOK_URL`.

Do not create `AZURE_CLIENT_SECRET` or a long-lived kubeconfig secret.

## OIDC and least privilege

Use separate federated identities:

- Build identity subject: `repo:<org>/<repo>:ref:refs/heads/master`; grant
  `AcrPush` only at the application ACR scope.
- Production identity subject:
  `repo:<org>/<repo>:environment:production`; grant AKS cluster-user access and
  a namespace-scoped Kubernetes/Azure RBAC writer role. Do not grant ACR push.
- AKS kubelet identity needs `AcrPull` on the application ACR.
- API workload identity needs `Key Vault Secrets User` only on its application
  vault when Key Vault integration is enabled.

The `platform` namespace must exist before deployment. The workflow deliberately
does not create namespaces so the deploy identity can remain namespace-scoped.

## Release and production approval

1. Open a PR and complete every field in the PR template.
2. Obtain an authorized approval and pass `PR CI / Quality Gate`.
3. Merge into `master`; direct pushes cannot produce a release.
4. Wait for `Build Release` to produce `release-evidence` successfully.
5. Dispatch `Deploy Production` from `master` with that Build Release run ID.
6. The production reviewer checks the PR, coverage and scan results, image
   digests, SBOMs, provenance, and rollback plan before approving the environment.
7. The deployment verifies rollout, service endpoints, the running image IDs,
   API health, database readiness, and the optional public route.

The release identity is:

```text
Pull request
  -> approved commit
  -> Build Release run
  -> ACR image digests
  -> SBOM + signed provenance + checksums
  -> production environment approval
  -> deployment run
  -> running image IDs + verification result
```

## Rollback

After a human decides to roll back, dispatch `Rollback Production` from `master`
with:

- the Build Release run ID of the stable artifact;
- the Helm revision containing that artifact;
- the decision rationale.

The workflow validates the old release evidence and Helm manifest before making a
change. It then repeats rollout, endpoint, digest, dependency, and smoke checks.
Rollback evidence is retained as a separate workflow artifact.
