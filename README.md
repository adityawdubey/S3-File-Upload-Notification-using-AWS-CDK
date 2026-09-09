# S3 File Upload Notification System using AWS CDK

[![CDK Deploy (main Branch)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/actions/workflows/dev.yaml/badge.svg)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/actions/workflows/dev.yaml)

This project is designed to provide a notification system for file uploads to an S3 bucket using AWS Lambda and other AWS services. When a file is uploaded to the specified S3 bucket, the system triggers a Lambda function which processes the file and sends notifications accordingly.
To implement the project step by step using the AWS Management Console, you can follow this project design narrative in my blog website: [https://adityadubey.tech/s3-file-upload-notification-system](https://adityadubey.tech/s3-file-upload-notification-system).

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup and Deployment](#setup-and-deployment)
- [Usage](#usage)
- [CI/CD](#cicd)
- [Cleanup](#cleanup)
- [Notes and Limitations](#notes-and-limitations)
- [References](#references)

## Architecture

![S3 Notification (4)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/assets/88245579/d57e9f6b-6900-49a4-97aa-e456cf724e4c)

The architecture consists of the following components:
- **S3 Bucket:** The designated storage location for uploaded files. Configured with an `ObjectCreated` event notification that invokes the Lambda function.
- **Lambda Function:** Triggered by S3 events. It extracts the bucket name, object key, and event timestamp from each record, sends that metadata to SQS, and publishes a notification message to SNS.
- **Amazon SNS (Simple Notification Service):** Delivers the notification to an email subscriber. The subscription endpoint is supplied at deploy time.
- **Amazon SQS (Simple Queue Service):** Receives the structured upload metadata as JSON, so downstream consumers can process uploads independently of the notification path.
- **Amazon CloudWatch:** Captures Lambda execution logs for observability and troubleshooting.

## Features

- **Automated Notifications:** Notifications are triggered automatically on any object upload to the S3 bucket.
- **Decoupled Metadata Path:** Upload metadata is written to SQS separately from the notification, so processing can be added later without changing the trigger.
- **Multi-Channel Capable:** SNS supports email, SMS, HTTPS, and other protocols. This stack subscribes an email endpoint by default.
- **Detailed Logging:** CloudWatch Logs capture function execution details for debugging and analysis.
- **Keyless CI/CD:** GitHub Actions deploys via OIDC role assumption, with no long-lived AWS access keys stored in the repository.

## Prerequisites

- **AWS Account:** An active AWS account is required to utilize the services.
- **AWS CLI:** Installed and configured on your local machine to interact with AWS resources.
- **AWS CDK CLI:** Streamlines the deployment of serverless applications on AWS.
  - Useful commands:
      - `cdk ls` lists all stacks in the app
      - `cdk synth` emits the synthesized CloudFormation template
      - `cdk deploy` deploys this stack to your default AWS account/region
      - `cdk diff` compares deployed stack with current state
      - `cdk docs` opens CDK documentation
- **Python 3.9 or later:** Required to run the CDK app. Note that the deployed Lambda function itself uses the `python3.8` runtime.
- **Docker:** Required at synth time. The Lambda layer is built with `PythonLayerVersion`, which bundles dependencies inside a container image.

## Setup and Deployment

### Clone the Repository

```bash
git clone https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK.git
cd S3-File-Upload-Notification-using-AWS-CDK
```

### Install Dependencies

Create a virtual environment and install the required packages.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure Environment Variables

The CDK app reads two required values from the environment via `python-dotenv`. Create a `.env` file in the repository root:

```bash
EMAIL_SUBSCRIPTION_ENDPOINT=you@example.com
FILE_UPLOAD_BUCKET=your-globally-unique-bucket-name
```

| Variable | Description |
|---|---|
| `EMAIL_SUBSCRIPTION_ENDPOINT` | Email address that receives upload notifications. |
| `FILE_UPLOAD_BUCKET` | Name of the S3 bucket to create. S3 bucket names are globally unique across all AWS accounts and regions, so pick something distinctive. |

`.env` is listed in `.gitignore` and must not be committed.

### Configure AWS CLI

Ensure your AWS CLI is configured with credentials that have permission to deploy CloudFormation stacks.

### Bootstrap the CDK Environment

CDK requires a one-time bootstrap per account and region pair. This provisions the staging bucket, ECR repository, and deployment roles that CDK uses.

```bash
cdk bootstrap aws://<ACCOUNT_ID>/<REGION>
```

Bootstrapping creates account-level IAM resources and needs elevated permissions, so it is run manually rather than from the deployment pipeline. To bootstrap several regions at once, pass multiple environments to the same command.

### Running the deployment Script

Make the script executable and run it.

```bash
chmod +x ./scripts/deploy.sh && ./scripts/deploy.sh
```

This script will:

- Bootstrap the CDK environment if it has not been done already.
- Synthesize the CloudFormation templates.
- Deploy the CDK stack.

### Confirm the SNS Subscription

AWS sends a confirmation email to `EMAIL_SUBSCRIPTION_ENDPOINT` after the first deploy. **You must click the confirmation link before any notifications will be delivered.** Until then the subscription stays in `PendingConfirmation` and SNS silently drops messages addressed to it. Verify with:

```bash
aws sns list-subscriptions --region <REGION> --output table
```

## Usage

Any file uploaded to the specified S3 bucket will trigger the Lambda function. The Lambda function publishes a notification via SNS and writes the upload metadata to SQS.

Upload a test file:

```bash
aws s3 cp ./test.txt s3://<FILE_UPLOAD_BUCKET>/
```

Check the Lambda logs:

```bash
aws logs tail /aws/lambda/<FUNCTION_NAME> --region <REGION> --since 10m --format short
```

## CI/CD

`.github/workflows/dev.yaml` deploys the stack on every push to `main`.

Authentication uses **GitHub OIDC** rather than stored access keys. The workflow requests a short-lived JSON Web Token from GitHub, exchanges it with AWS STS for temporary credentials, and assumes a deployment role. No long-lived AWS credentials exist in the repository.

Required setup on the AWS side:

1. An IAM OIDC identity provider for `token.actions.githubusercontent.com` with audience `sts.amazonaws.com`.
2. An IAM role whose trust policy restricts `token.actions.githubusercontent.com:sub` to this repository and environment:
   ```
   repo:<OWNER>/<REPO>:environment:development
   ```
3. A permissions policy on that role allowing `sts:AssumeRole` on the `cdk-hnb659fds-*` bootstrap roles and `ssm:GetParameter` on `/cdk-bootstrap/hnb659fds/version`. The bootstrap roles hold the actual deployment permissions, so the CI role needs nothing more.

Required setup on the GitHub side, under **Settings > Environments > development**:

| Variable | Description |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN of the IAM role the workflow assumes. |
| `EMAIL_SUBSCRIPTION_ENDPOINT` | Email address for notifications. |
| `FILE_UPLOAD_BUCKET` | Target S3 bucket name. |

Set **Deployment branches and tags** on the `development` environment to `main`. Because the role trust policy is scoped to the environment rather than a branch, this restriction is what prevents other branches from reaching the role.

The workflow also needs `id-token: write` permission to request the OIDC token. Without it the credential step fails before reaching AWS.

Bootstrapping is intentionally excluded from the pipeline. It creates account-level IAM roles and would require granting the CI role admin-equivalent permissions, which would defeat the least-privilege setup above.

## Cleanup

```bash
cdk destroy --all
```

The S3 bucket is configured with `RemovalPolicy.DESTROY` and `auto_delete_objects=True`, so it is removed along with its contents.

## Notes and Limitations

- **Lambda runtime:** The function targets `python3.8`, which is past AWS standard support. Upgrading to `python3.12` or later is recommended.
- **Redundant Lambda layer:** `lambda_layer/requirements.txt` contains only `boto3`, which is already included in the Lambda runtime. The layer adds Docker build time at synth without providing anything new, and can be removed unless a specific `boto3` version is needed.
- **SQS is an extension point:** SQS is included for future background processing and is not needed for the email notification feature currently implemented. Upload metadata is written to the queue, but no consumer reads it yet; email notifications are published directly to SNS by Lambda.
- **No dead-letter queue:** S3 invokes the function asynchronously. On failure Lambda retries twice and then discards the event, leaving no record beyond CloudWatch. Adding a DLQ or an `on_failure` destination is recommended before relying on this in production.
- **Bucket removal policy:** `RemovalPolicy.DESTROY` with `auto_delete_objects=True` is convenient for a demo but will delete real data on stack teardown. Change it before production use.
- **`scripts/delete.sh` is empty.** Use `cdk destroy --all` for teardown.

## References

- https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html
- https://docs.aws.amazon.com/cdk/v2/guide/environments.html
- https://docs.aws.amazon.com/cdk/v2/guide/bootstrapping.html
- https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- https://github.com/aws-actions/configure-aws-credentials
