import boto3
import json

ENDPOINT = "http://localhost:4566"
REGION = "us-east-1"

BUCKET = "careerwise-resumes"
FUNCTION_NAME = "CareerCloudResumeScreening"

lambda_client = boto3.client(
    "lambda",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

s3_client = boto3.client(
    "s3",
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

# Get Lambda ARN
function = lambda_client.get_function(
    FunctionName=FUNCTION_NAME
)

lambda_arn = function["Configuration"]["FunctionArn"]

print("Lambda ARN:")
print(lambda_arn)

# Allow S3 to invoke Lambda
try:
    lambda_client.add_permission(
        FunctionName=FUNCTION_NAME,
        StatementId="AllowS3InvokeResumeScreening",
        Action="lambda:InvokeFunction",
        Principal="s3.amazonaws.com",
        SourceArn=f"arn:aws:s3:::{BUCKET}",
        SourceAccount="000000000000"
    )

    print("Lambda permission added.")

except lambda_client.exceptions.ResourceConflictException:
    print("Lambda permission already exists.")

# Configure S3 notification
configuration = {
    "LambdaFunctionConfigurations": [
        {
            "LambdaFunctionArn": lambda_arn,
            "Events": [
                "s3:ObjectCreated:*"
            ],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "resume/"
                        }
                    ]
                }
            }
        }
    ]
}

s3_client.put_bucket_notification_configuration(
    Bucket=BUCKET,
    NotificationConfiguration=configuration
)

print("\nS3 -> Lambda trigger configured successfully.")

# Verify
result = s3_client.get_bucket_notification_configuration(
    Bucket=BUCKET
)

print("\nCurrent notification configuration:")
print(json.dumps(result, indent=2))