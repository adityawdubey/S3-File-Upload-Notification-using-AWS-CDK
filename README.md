# S3 File Upload Notification System using AWS CDK

[![CDK Deploy (main Branch)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/workflows/dev.yaml/badge.svg)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/actions/workflows/dev.yaml)

This project is designed to provide a notification system for file uploads to an S3 bucket using AWS Lambda and other AWS services. When a file is uploaded to the specified S3 bucket, the system triggers a Lambda function which processes the file and sends notifications accordingly. 
To implement the project step by step using the AWS Management Console, you can follow this project design narrative in my blog website: [https://adityadubey.cloud/s3-file-upload-notification-system](https://adityadubey.cloud/s3-file-upload-notification-system).

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup and Deployment](#setup-and-deployment)
- [Usage](#usage)

## Architecture

![S3 Notification (4)](https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK/assets/88245579/d57e9f6b-6900-49a4-97aa-e456cf724e4c)

The architecture consists of the following components:
- **S3 Bucket:** The designated storage location for uploaded files.
- **Lambda Function:** The heart of the system, automatically triggered by S3 events (file uploads), it processes the uploaded file and initiates notifications.
- **Amazon SNS (Simple Notification Service):** Used to send notifications to subscribers via various channels (email, SMS, etc.).
- **Amazon CloudWatch:** Provides logging and monitoring of the Lambda function's execution, ensuring observability and troubleshooting capabilities.
- **Amazon SQS (Simple Queue Service):** Used for decoupling and scaling the processing of uploaded files.

## Features

- **Automated Notifications:** Instantly trigger notifications upon file uploads to the S3 bucket.
- **Flexible Processing:** The Lambda function can be customized to perform file validation, data extraction, or other processing actions before sending notifications.
- **Multi-Channel Notifications:** Leverage SNS to deliver notifications via email, SMS, or other supported protocols.
- **Detailed Logging:** CloudWatch Logs capture function execution details for debugging and analysis.

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
- **Python 3.8+:** The Lambda function is written in Python.
- **jq:** A command-line JSON processor (optional, for working with JSON output).

## Setup and Deployment

### Clone the Repository

```bash
git clone https://github.com/adityawdubey/S3-File-Upload-Notification-using-AWS-CDK.git
cd S3-File-Upload-Notification-using-AWS-CDK
```
### Install Dependencies

Create Virtual Environment and install required packages
```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configure AWS CLI
Ensure your AWS CLI is configured with the necessary permissions.

### Add dev parameters
Ensure the dev-parameters.json file is updated with your specific configurations and is added to .gitignore

### Running the deployment Script

Make the script Executable and Run the script.

```
chmod +x ././scripts/deploy.sh && ./scripts/deploy.sh
```
This script will:

- Export the parameters from dev-parameters.json to environment variables.
- Bootstrap the CDK environment if it has not been done already.
- Synthesize the CloudFormation templates.
- Deploy the CDK stack.

## Usage

Any file uploaded to the specified S3 bucket will trigger the Lambda function. The Lambda function processes the file and sends a notification via SNS. 

## References

- https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html 
- https://docs.aws.amazon.com/cdk/v2/guide/environments.html
- https://docs.aws.amazon.com/cdk/v2/guide/configure-env.html#:~:text=To%20pass%20environment%20variables%2C%20use,values%20of%20these%20environment%20variables. 
