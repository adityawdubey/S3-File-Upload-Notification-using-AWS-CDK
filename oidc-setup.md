# GitHub Actions OIDC Authentication

Migrated GitHub Actions deployment from stored AWS credentials to OIDC.

Previously the workflow authenticated with `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` stored as GitHub secrets — long-lived credentials that never rotated and would stay valid to anyone who extracted them.

Now the runner requests a short-lived OIDC token from GitHub and exchanges it with AWS STS for temporary credentials scoped to a single job run. Nothing persistent is stored in the repository.

What it took:

1. Registered `token.actions.githubusercontent.com` as an IAM OIDC identity provider (audience `sts.amazonaws.com`).
2. Created a deploy role whose trust policy pins `sub` to `repo:<owner>/<repo>:environment:development`, so only that repo and environment can assume it.
3. Scoped its permissions to two actions: assume the CDK bootstrap roles, and read the bootstrap version parameter. The bootstrap roles hold the real deploy permissions, so the CI role needs nothing more.
4. Added `id-token: write` to the workflow, swapped the key inputs for `role-to-assume`, and updated the actions to current versions.
5. Restricted the `development` environment to `main`, since the trust policy keys on environment rather than branch.
6. Deleted the old access keys and GitHub secrets.

CDK bootstrapping stayed manual and out of the pipeline — automating it would have required granting the CI role admin-equivalent IAM permissions, which would have undone the point.

## How the exchange works

```
1. Job starts, declares environment: development
2. Runner asks GitHub's OIDC provider for a JWT
   The JWT's `sub` claim describes the job: repo:<owner>/<repo>:environment:development
3. Runner calls sts:AssumeRoleWithWebIdentity with that JWT
4. AWS validates the signature against GitHub's public keys (JWKS),
   then checks the JWT's claims against the role's trust policy
5. STS returns temporary credentials, valid ~1 hour, scoped to this run
```

The trust policy is the security boundary. It is what stops any other repository, or any other environment in this repository, from assuming the role even though the identity provider itself is account-wide.

## AWS setup

Replace `<ACCOUNT_ID>`, `<OWNER>`, `<REPO>`, and `<REGION>` throughout. IAM is global, so no region applies to steps 1 and 2; the permissions policy in step 3 is region-specific because the bootstrap roles and version parameter are.

### 1. Create the identity provider

**IAM > Identity providers > Add provider**

| Field | Value |
|---|---|
| Provider type | OpenID Connect |
| Provider URL | `https://token.actions.githubusercontent.com` |
| Audience | `sts.amazonaws.com` |

The console requires clicking **Get thumbprint** before it will accept the form. The retrieved value is effectively cosmetic: AWS verifies GitHub's JWKS endpoint against its own trusted certificate authority library and falls back to thumbprints only for providers using untrusted certificates. Guides that hardcode a specific thumbprint are pinning something that no longer matters.

Only one provider for this URL can exist per account. If it is already listed, skip this step.

### 2. Create the deploy role

**IAM > Roles > Create role > Web identity**, selecting the provider above and audience `sts.amazonaws.com`.

The console wizard offers organization, repository, and branch fields, which generate a `sub` ending in `:ref:refs/heads/<branch>`. That does not match a job which declares an `environment`. Leave the branch field blank and replace the generated trust policy with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
          "token.actions.githubusercontent.com:sub": "repo:<OWNER>/<REPO>:environment:development"
        }
      }
    }
  ]
}
```

Both conditions use `StringEquals` rather than `StringLike`. With one repository and one environment there is nothing to wildcard, and a stray wildcard here widens who can assume the role.

IAM does not expose arbitrary JWT claims as condition keys. For identity providers using the default OIDC mapping, which is the one GitHub Actions uses, AWS STS exposes only `amr`, `aud`, `email`, `oaud`, and `sub`. GitHub's token also carries `repository`, `ref`, `environment`, `actor`, and `job_workflow_ref`, but none of those are usable in a `Condition` block, and `email` is absent from GitHub's token entirely.

This is why `sub` carries the whole restriction: GitHub encodes repository, environment, and ref into that single string precisely because it is the only claim available to condition on.

### 3. Attach permissions

An inline policy on the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeCdkBootstrapRoles",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::<ACCOUNT_ID>:role/cdk-hnb659fds-*-<ACCOUNT_ID>-<REGION>"
    },
    {
      "Sid": "ReadBootstrapVersion",
      "Effect": "Allow",
      "Action": "ssm:GetParameter",
      "Resource": "arn:aws:ssm:<REGION>:<ACCOUNT_ID>:parameter/cdk-bootstrap/hnb659fds/version"
    }
  ]
}
```

Two permissions total. CDK bootstrap has already created five roles that carry the real deployment rights, so this role only needs to assume them:

| Bootstrap role | Responsibility |
|---|---|
| `cdk-hnb659fds-deploy-role-*` | Drives the CloudFormation deployment |
| `cdk-hnb659fds-file-publishing-role-*` | Uploads Lambda and layer assets to the staging bucket |
| `cdk-hnb659fds-image-publishing-role-*` | Pushes container image assets to ECR |
| `cdk-hnb659fds-lookup-role-*` | Read-only context lookups during synth |
| `cdk-hnb659fds-cfn-exec-role-*` | Assumed by CloudFormation to create resources |

The wildcard in the policy resource above matches all five, since every one follows the `cdk-hnb659fds-<purpose>-<account>-<region>` naming pattern.

Attaching `AdministratorAccess` here instead would work and would discard the entire benefit.

## GitHub setup

Under **Settings > Environments > development**:

| Variable | Description |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the role created above |
| `EMAIL_SUBSCRIPTION_ENDPOINT` | Notification email address |
| `FILE_UPLOAD_BUCKET` | Target S3 bucket name |

Set **Deployment branches and tags** to **Selected branches and tags** and add `main`.

This restriction is load-bearing. The trust policy pins to the environment, not to a branch, so the environment's own branch rule is what prevents a feature branch from reaching the role.

## Workflow changes

```yaml
permissions:
  contents: read          # for actions/checkout
  id-token: write         # REQUIRED - lets the runner request the OIDC JWT

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: development

    steps:
      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v6
        with:
          role-to-assume: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
          role-session-name: gha-s3-upload-notification-${{ github.run_id }}
          aws-region: <REGION>
```

Declaring `permissions:` overrides the defaults entirely, so `contents: read` must be listed explicitly or `actions/checkout` breaks.

## Troubleshooting

| Symptom | Cause |
|---|---|
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | The `sub` in the trust policy does not match the JWT. Most often the console wizard's `:ref:refs/heads/main` form was kept on a job that declares an `environment`. |
| `Credentials could not be loaded` | `id-token: write` is missing from `permissions:`. The runner cannot mint a JWT at all. |
| `no identity-based policy allows the <action>` | Nothing attached to the role grants that action. This wording means no match was found, as opposed to an explicit `Deny` or a failed condition. |
| `SSM parameter /cdk-bootstrap/hnb659fds/version not found` | The target account and region were never bootstrapped. Bootstrap is per account and region pair. |
| `current credentials could not be used to assume ... Proceeding anyway` | The bootstrap roles do not exist, or the role lacks `sts:AssumeRole` on them. Once everything is correct, this line disappears. |
| An error naming `sts:TagSession` | Add `role-skip-session-tagging: true` to the action's `with:` block. |

## References

- https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-idp_oidc.html
- https://github.com/aws-actions/configure-aws-credentials
- https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html
