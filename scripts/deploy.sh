#!/bin/bash

# Ensure the script stops on errors
set -e

# Path to the environment parameters file
ENV_FILE="parameters/dev-parameters.json"

# Check if the parameters file exists
if [ -f "$ENV_FILE" ]; then
    # Export parameters as environment variables
    export EMAIL_SUBSCRIPTION_ENDPOINT=$(jq -r '.[] | select(.ParameterKey=="EmailSubscriptionEndpoint") | .ParameterValue' "$ENV_FILE")
    export FILE_UPLOAD_BUCKET=$(jq -r '.[] | select(.ParameterKey=="FileUploadDestinationBucket") | .ParameterValue' "$ENV_FILE")
else
    echo "Parameters file $ENV_FILE not found!"
    exit 1
fi

# Bootstrap CDK environment (if not already done)
cdk bootstrap

# Synthesize CloudFormation templates
cdk synth

cdk deploy --all 
