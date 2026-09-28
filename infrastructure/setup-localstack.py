import os
import json
import time
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


# ============================================================
# Configuration
# ============================================================

REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
ENDPOINT = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:4566")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS_DIR = PROJECT_ROOT / "backend" / "functions"

ROLE_NAME = "CareerCloudLambdaRole"
ROLE_ARN = f"arn:aws:iam::000000000000:role/{ROLE_NAME}"

API_NAME = "CareerCloudAPI"
STAGE_NAME = "dev"

LAMBDA_CONFIG = {
    "CareerCloudUsers": {
        "folder": "users",
        "zip": "users-lambda.zip",
        "handler": "handler.lambda_handler",
        "timeout": 3,
    },
    "CareerCloudAssessment": {
        "folder": "assessment",
        "zip": "assessment-lambda.zip",
        "handler": "handler.lambda_handler",
        "timeout": 3,
    },
    "CareerCloudRecommendation": {
        "folder": "recommendation",
        "zip": "recommendation-lambda.zip",
        "handler": "handler.lambda_handler",
        "timeout": 60,
    },
    "CareerCloudRoadmap": {
        "folder": "roadmap",
        "zip": "roadmap-lambda.zip",
        "handler": "handler.lambda_handler",
        "timeout": 60,
    },
}


# ============================================================
# Clients
# ============================================================

session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    region_name=REGION,
)

iam = session.client("iam", endpoint_url=ENDPOINT)
lambda_client = session.client("lambda", endpoint_url=ENDPOINT)
apigateway = session.client("apigateway", endpoint_url=ENDPOINT)


# ============================================================
# Environment variables for Lambdas
# ============================================================

common_env = {
    "AWS_REGION": REGION,
    "DYNAMODB_ENDPOINT": ENDPOINT,
}

gemini_key = os.getenv("GEMINI_API_KEY")

environments = {
    "CareerCloudUsers": {
        **common_env,
        "USERS_TABLE": "CareerCloudUsers",
        "ASSESSMENTS_TABLE": "CareerAssessments",
        "RECOMMENDATIONS_TABLE": "CareerRecommendations",
        "ROADMAPS_TABLE": "LearningRoadmaps",
    },

    "CareerCloudAssessment": {
        **common_env,
        "ASSESSMENTS_TABLE": "CareerAssessments",
    },

    "CareerCloudRecommendation": {
        **common_env,
        "ASSESSMENTS_TABLE": "CareerAssessments",
        "RECOMMENDATIONS_TABLE": "CareerRecommendations",
    },

    "CareerCloudRoadmap": {
        **common_env,
        "RECOMMENDATIONS_TABLE": "CareerRecommendations",
        "ROADMAPS_TABLE": "LearningRoadmaps",
    },
}

# Only add Gemini key to the functions that actually need it.
# Never print the key.
if gemini_key:
    environments["CareerCloudRecommendation"]["GEMINI_API_KEY"] = gemini_key
    environments["CareerCloudRoadmap"]["GEMINI_API_KEY"] = gemini_key


# ============================================================
# Helpers
# ============================================================

def log(message):
    print(f"[CareerCloud] {message}")


def get_zip_path(function_name):
    config = LAMBDA_CONFIG[function_name]
    return FUNCTIONS_DIR / config["folder"] / config["zip"]


def lambda_exists(function_name):
    try:
        lambda_client.get_function(FunctionName=function_name)
        return True
    except lambda_client.exceptions.ResourceNotFoundException:
        return False


def get_role():
    try:
        response = iam.get_role(RoleName=ROLE_NAME)
        return response["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        return None


# ============================================================
# IAM Role
# ============================================================

def ensure_iam_role():
    log("Checking IAM role...")

    existing_role = get_role()

    if existing_role:
        log(f"IAM role already exists: {ROLE_NAME}")
        return existing_role

    log("IAM role does not exist. Creating it...")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
            }
        ],
    }

    response = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=json.dumps(trust_policy),
        Description="CareerCloud Lambda execution role",
    )

    role_arn = response["Role"]["Arn"]

    log(f"Created IAM role: {role_arn}")

    return role_arn


# ============================================================
# Lambda
# ============================================================
def ensure_lambda(function_name, role_arn):
    config = LAMBDA_CONFIG[function_name]
    zip_path = get_zip_path(function_name)

    if not zip_path.exists():
        raise FileNotFoundError(
            f"Lambda ZIP not found: {zip_path}"
        )

    log(f"Processing Lambda: {function_name}")
    log(f"ZIP: {zip_path}")

    code_bytes = zip_path.read_bytes()

    env_vars = environments[function_name]

    if lambda_exists(function_name):
        log(f"Lambda exists. Updating: {function_name}")

        # ----------------------------------------------------
        # 1. Update Lambda code
        # ----------------------------------------------------
        lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=code_bytes,
            Publish=True,
        )

        # ----------------------------------------------------
        # 2. Wait for code update to finish
        # ----------------------------------------------------
        log(f"Waiting for code update: {function_name}")

        for attempt in range(30):
            status = lambda_client.get_function_configuration(
                FunctionName=function_name
            )

            last_update_status = status.get("LastUpdateStatus")

            if last_update_status == "Successful":
                break

            if last_update_status == "Failed":
                raise RuntimeError(
                    f"Lambda code update failed for {function_name}"
                )

            time.sleep(1)

        else:
            raise TimeoutError(
                f"Timed out waiting for {function_name} code update"
            )

        # ----------------------------------------------------
        # 3. Update Lambda configuration
        # ----------------------------------------------------
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=role_arn,
            Handler=config["handler"],
            Timeout=config["timeout"],
            Environment={
                "Variables": env_vars
            },
        )

        # ----------------------------------------------------
        # 4. Wait for configuration update
        # ----------------------------------------------------
        log(f"Waiting for configuration update: {function_name}")

        for attempt in range(30):
            status = lambda_client.get_function_configuration(
                FunctionName=function_name
            )

            last_update_status = status.get("LastUpdateStatus")

            if last_update_status == "Successful":
                break

            if last_update_status == "Failed":
                raise RuntimeError(
                    f"Lambda configuration update failed for {function_name}"
                )

            time.sleep(1)

        else:
            raise TimeoutError(
                f"Timed out waiting for {function_name} configuration update"
            )

    else:
        log(f"Lambda does not exist. Creating: {function_name}")

        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=role_arn,
            Handler=config["handler"],
            Code={
                "ZipFile": code_bytes
            },
            Timeout=config["timeout"],
            Environment={
                "Variables": env_vars
            },
            Publish=True,
        )

    log(f"Lambda ready: {function_name}")
# ============================================================
# API Gateway
# ============================================================

def get_api():
    response = apigateway.get_rest_apis()

    for api in response.get("items", []):
        if api.get("name") == API_NAME:
            return api

    return None


def get_resources(rest_api_id):
    response = apigateway.get_resources(
        restApiId=rest_api_id,
        limit=500,
    )

    return response.get("items", [])


def find_resource(resources, path_part, parent_id):
    for resource in resources:
        if (
            resource.get("pathPart") == path_part
            and resource.get("parentId") == parent_id
        ):
            return resource

    return None


def ensure_resource(rest_api_id, resources, path_part, parent_id):
    existing = find_resource(
        resources,
        path_part,
        parent_id,
    )

    if existing:
        log(
            f"API resource already exists: "
            f"{path_part} ({existing['id']})"
        )
        return existing

    response = apigateway.create_resource(
        restApiId=rest_api_id,
        parentId=parent_id,
        pathPart=path_part,
    )

    resource = response

    log(
        f"Created API resource: "
        f"{path_part} ({resource['id']})"
    )

    return resource


def ensure_post_method(
    rest_api_id,
    resource_id,
    function_name,
):
    lambda_uri = (
        f"arn:aws:apigateway:{REGION}:"
        f"lambda:path/2015-03-31/functions/"
        f"arn:aws:lambda:{REGION}:000000000000:"
        f"{function_name}/invocations"
    )

    try:
        apigateway.get_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod="POST",
        )

        log(
            f"POST method already exists for "
            f"{function_name}"
        )

    except apigateway.exceptions.NotFoundException:

        apigateway.put_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod="POST",
            authorizationType="NONE",
        )

        log(
            f"Created POST method for "
            f"{function_name}"
        )

    apigateway.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod="POST",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=lambda_uri,
    )

    log(
        f"Configured API integration: "
        f"POST -> {function_name}"
    )


def ensure_get_method(
    rest_api_id,
    resource_id,
    function_name,
):
    lambda_uri = (
        f"arn:aws:apigateway:{REGION}:"
        f"lambda:path/2015-03-31/functions/"
        f"arn:aws:lambda:{REGION}:000000000000:"
        f"{function_name}/invocations"
    )

    try:
        apigateway.get_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod="GET",
        )

        log("GET method already exists")

    except apigateway.exceptions.NotFoundException:

        apigateway.put_method(
            restApiId=rest_api_id,
            resourceId=resource_id,
            httpMethod="GET",
            authorizationType="NONE",
        )

        log("Created GET method")

    apigateway.put_integration(
        restApiId=rest_api_id,
        resourceId=resource_id,
        httpMethod="GET",
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=lambda_uri,
    )

    log(
        f"Configured GET integration: "
        f"GET -> {function_name}"
    )


def ensure_api_gateway():
    log("Checking API Gateway...")

    api = get_api()

    if api:
        rest_api_id = api["id"]
        log(
            f"API already exists: "
            f"{API_NAME} ({rest_api_id})"
        )
    else:
        response = apigateway.create_rest_api(
            name=API_NAME,
            description="CareerCloud AI API",
        )

        rest_api_id = response["id"]

        log(
            f"Created API: "
            f"{API_NAME} ({rest_api_id})"
        )

    resources = get_resources(rest_api_id)

    root = next(
        r for r in resources
        if r.get("path") == "/"
    )

    # /users
    users = ensure_resource(
        rest_api_id,
        resources,
        "users",
        root["id"],
    )

    ensure_post_method(
        rest_api_id,
        users["id"],
        "CareerCloudUsers",
    )

    # /users/{userId}
    resources = get_resources(rest_api_id)

    user_id_resource = find_resource(
        resources,
        "{userId}",
        users["id"],
    )

    if not user_id_resource:
        user_id_resource = apigateway.create_resource(
            restApiId=rest_api_id,
            parentId=users["id"],
            pathPart="{userId}",
        )

        log(
            f"Created API resource: "
            f"/users/{{userId}}"
        )

    ensure_get_method(
        rest_api_id,
        user_id_resource["id"],
        "CareerCloudUsers",
    )

    # /assessment
    resources = get_resources(rest_api_id)

    assessment = ensure_resource(
        rest_api_id,
        resources,
        "assessment",
        root["id"],
    )

    ensure_post_method(
        rest_api_id,
        assessment["id"],
        "CareerCloudAssessment",
    )

    # /recommendation
    resources = get_resources(rest_api_id)

    recommendation = ensure_resource(
        rest_api_id,
        resources,
        "recommendation",
        root["id"],
    )

    ensure_post_method(
        rest_api_id,
        recommendation["id"],
        "CareerCloudRecommendation",
    )

    # /roadmap
    resources = get_resources(rest_api_id)

    roadmap = ensure_resource(
        rest_api_id,
        resources,
        "roadmap",
        root["id"],
    )

    ensure_post_method(
        rest_api_id,
        roadmap["id"],
        "CareerCloudRoadmap",
    )

    # Deployment
    log("Creating API Gateway deployment...")

    deployment = apigateway.create_deployment(
        restApiId=rest_api_id,
        stageName=STAGE_NAME,
        description="CareerCloud recovery deployment",
    )

    deployment_id = deployment["id"]

    log(
        f"API deployed: "
        f"stage={STAGE_NAME}, "
        f"deployment={deployment_id}"
    )

    invoke_url = (
        f"http://{rest_api_id}.execute-api."
        f"{REGION}.localhost.localstack.cloud:4566/"
        f"{STAGE_NAME}"
    )

    log(f"API Base URL: {invoke_url}")

    return rest_api_id


# ============================================================
# Main
# ============================================================

def main():

    print()
    print("=" * 60)
    print("CareerCloud AI - LocalStack Recovery")
    print("=" * 60)
    print()

    log(f"Project root: {PROJECT_ROOT}")
    log(f"LocalStack endpoint: {ENDPOINT}")
    log(f"Region: {REGION}")

    print()

    # IMPORTANT:
    # This script intentionally does NOT create, delete,
    # or modify DynamoDB tables.
    log("DynamoDB tables will NOT be created, deleted, or modified.")

    print()

    # IAM
    role_arn = ensure_iam_role()

    print()

    # Lambdas
    for function_name in LAMBDA_CONFIG:
        ensure_lambda(
            function_name,
            role_arn,
        )

    print()

    # API Gateway
    api_id = ensure_api_gateway()

    print()

    # Final Lambda verification
    log("Final Lambda verification:")

    response = lambda_client.list_functions()

    for function in response.get("Functions", []):
        name = function["FunctionName"]

        if name.startswith("CareerCloud"):
            log(
                f"{name} | "
                f"Runtime={function.get('Runtime')} | "
                f"Timeout={function.get('Timeout')} | "
                f"Handler={function.get('Handler')}"
            )

    print()

    log(f"API Gateway ID: {api_id}")
    log("Recovery completed successfully.")

    print()
    print("=" * 60)
    print("CareerCloud LocalStack recovery complete")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()