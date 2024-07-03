#!/bin/bash

# Ensure the script stops on errors
set -e

# Bootstrap CDK environment (if not already done)
cdk bootstrap

# Synthesize CloudFormation templates
cdk synth

# Deploy the stack
echo "Deploying the stack..."
cdk deploy --all
echo "Deployment process completed."