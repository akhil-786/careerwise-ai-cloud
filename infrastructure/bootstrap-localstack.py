"""Create/update the CareerCloud local-development resources in LocalStack."""
import json
import os
import secrets
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
REGION = os.getenv("AWS_REGION", "us-east-1")
ACCESS = dict(
    endpoint_url=ENDPOINT,
    region_name=REGION,
    aws_access_key_id="test",
    aws_secret_access_key="test",
)
LAMBDA_ROLE = "arn:aws:iam::000000000000:role/CareerCloudLambdaRole"
API_NAME = "CareerCloudAPI"
BUCKET = "careerwise-resumes"
FUNCTIONS = {
    "CareerCloudAuth": ("backend/functions/auth/auth-lambda-localstack.zip", 10, {
        "USERS_TABLE": "CareerCloudUsers"}),
    "CareerCloudUsers": ("backend/functions/users/users-lambda-localstack.zip", 15, {
        "USERS_TABLE": "CareerCloudUsers", "ASSESSMENTS_TABLE": "CareerAssessments",
        "RECOMMENDATIONS_TABLE": "CareerRecommendations", "ROADMAPS_TABLE": "LearningRoadmaps",
        "SCREENINGS_TABLE": "ResumeScreenings"}),
    "CareerCloudAssessment": ("backend/functions/assessment/assessment-lambda-localstack.zip", 15, {
        "ASSESSMENTS_TABLE": "CareerAssessments"}),
    "CareerCloudRecommendation": ("backend/functions/recommendation/recommendation-lambda-localstack.zip", 60, {
        "ASSESSMENTS_TABLE": "CareerAssessments", "RECOMMENDATIONS_TABLE": "CareerRecommendations",
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")}),
    "CareerCloudRoadmap": ("backend/functions/roadmap/roadmap-lambda-localstack.zip", 60, {
        "RECOMMENDATIONS_TABLE": "CareerRecommendations", "ROADMAPS_TABLE": "LearningRoadmaps",
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "")}),
    "CareerCloudResumeScreening": ("backend/functions/resume-screening/resume-screening-lambda-localstack.zip", 60, {
        "SCREENINGS_TABLE": "ResumeScreenings", "RESUME_BUCKET": BUCKET}),
}
TABLES = {
    "CareerCloudUsers": "userId", "CareerAssessments": "assessmentId",
    "CareerRecommendations": "recommendationId", "LearningRoadmaps": "roadmapId",
    "ResumeScreenings": "screeningId",
}


def aws(name):
    return boto3.client(name, **ACCESS)


def ensure_table(ddb, name, key):
    if name in ddb.list_tables()["TableNames"]:
        return
    ddb.create_table(TableName=name,
        KeySchema=[{"AttributeName": key, "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": key, "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST")
    ddb.get_waiter("table_exists").wait(TableName=name)


def ensure_bucket(s3):
    if BUCKET not in [b["Name"] for b in s3.list_buckets()["Buckets"]]:
        s3.create_bucket(Bucket=BUCKET)
    s3.put_bucket_cors(Bucket=BUCKET, CORSConfiguration={"CORSRules": [{
        "AllowedOrigins": ["http://localhost:5173"], "AllowedMethods": ["PUT"],
        "AllowedHeaders": ["*"], "ExposeHeaders": ["ETag"], "MaxAgeSeconds": 3000}]})


def ensure_function(client, name, path, timeout, env):
    zip_path = ROOT / path
    if not zip_path.is_file():
        raise FileNotFoundError(zip_path)
    code = zip_path.read_bytes()
    try:
        old_config = client.get_function_configuration(FunctionName=name)
        exists = True
    except client.exceptions.ResourceNotFoundException:
        old_config = {}
        exists = False
    variables = dict(old_config.get("Environment", {}).get("Variables", {})) if exists else {}
    variables.update({"AWS_REGION": REGION,
        "DYNAMODB_ENDPOINT": "http://host.docker.internal:4566",
        "S3_ENDPOINT": "http://host.docker.internal:4566",
        "S3_PUBLIC_ENDPOINT": "http://localhost:4566", **env})
    if name == "CareerCloudAuth" and not variables.get("AUTH_SECRET"):
        variables["AUTH_SECRET"] = secrets.token_urlsafe(48)
    config = {"FunctionName": name, "Handler": "handler.lambda_handler",
        "Runtime": "python3.12", "Role": LAMBDA_ROLE, "Timeout": timeout,
        "MemorySize": 512 if timeout > 15 else 256,
        "Environment": {"Variables": variables}}
    if exists:
        client.update_function_code(FunctionName=name, ZipFile=code)
        client.get_waiter("function_updated").wait(FunctionName=name)
        client.update_function_configuration(FunctionName=name,
            Role=LAMBDA_ROLE, Handler=config["Handler"], Runtime=config["Runtime"],
            Timeout=timeout, MemorySize=config["MemorySize"], Environment=config["Environment"])
        client.get_waiter("function_updated").wait(FunctionName=name)
    else:
        client.create_function(**config, Code={"ZipFile": code}, Publish=True)
        client.get_waiter("function_active").wait(FunctionName=name)


def ensure_permission(lmb, function, statement, principal, source_arn):
    try:
        lmb.add_permission(FunctionName=function, StatementId=statement,
            Action="lambda:InvokeFunction", Principal=principal, SourceArn=source_arn)
    except lmb.exceptions.ResourceConflictException:
        pass


def main():
    ddb, s3, lmb, apigw = (aws("dynamodb"), aws("s3"), aws("lambda"), aws("apigateway"))
    for table, key in TABLES.items():
        ensure_table(ddb, table, key)
    ensure_bucket(s3)
    for name, (zip_path, timeout, env) in FUNCTIONS.items():
        ensure_function(lmb, name, zip_path, timeout, env)

    api = next((x for x in apigw.get_rest_apis()["items"] if x["name"] == API_NAME), None)
    if api is None:
        api = apigw.create_rest_api(name=API_NAME, description="CareerCloud local API")
    api_id = api["id"]
    resources = apigw.get_resources(restApiId=api_id)["items"]
    by_path = {x["path"]: x for x in resources}
    root_id = next(x["id"] for x in resources if x["path"] == "/")

    def resource(path):
        if path in by_path:
            return by_path[path]["id"]
        parent_path, _, leaf = path.rpartition("/")
        parent = resource(parent_path or "/")
        item = apigw.create_resource(restApiId=api_id, parentId=parent, pathPart=leaf)
        by_path[path] = item
        return item["id"]

    route_map = {
        ("POST", "/auth/register"): ("CareerCloudAuth", False),
        ("POST", "/auth/login"): ("CareerCloudAuth", False),
        ("POST", "/users"): ("CareerCloudUsers", True),
        ("GET", "/users/{userId}"): ("CareerCloudUsers", True),
        ("PUT", "/users/{userId}/skills"): ("CareerCloudUsers", True),
        ("GET", "/dashboard/{userId}"): ("CareerCloudUsers", True),
        ("POST", "/assessment"): ("CareerCloudAssessment", True),
        ("POST", "/recommendation"): ("CareerCloudRecommendation", True),
        ("POST", "/roadmap"): ("CareerCloudRoadmap", True),
        ("POST", "/resume/upload-url"): ("CareerCloudResumeScreening", True),
        ("GET", "/resume/{screeningId}"): ("CareerCloudResumeScreening", True),
    }
    auth = next((x for x in apigw.get_authorizers(restApiId=api_id)["items"]
        if x["name"] == "CareerCloudLocalAuth"), None)
    if auth is None:
        auth = apigw.create_authorizer(restApiId=api_id, name="CareerCloudLocalAuth",
            type="TOKEN", authorizerUri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/arn:aws:lambda:{REGION}:000000000000:function:CareerCloudAuth/invocations",
            identitySource="method.request.header.Authorization", authorizerResultTtlInSeconds=0)
    auth_id = auth["id"]
    for (method, path), (function, protected) in route_map.items():
        rid = resource(path)
        existing = apigw.get_resources(restApiId=api_id)["items"]
        methods = next(x for x in existing if x["id"] == rid).get("resourceMethods", {})
        if method not in methods:
            apigw.put_method(restApiId=api_id, resourceId=rid, httpMethod=method,
                authorizationType="CUSTOM" if protected else "NONE",
                authorizerId=auth_id if protected else "")
        else:
            apigw.update_method(restApiId=api_id, resourceId=rid, httpMethod=method,
                patchOperations=[{"op": "replace", "path": "/authorizationType", "value": "CUSTOM" if protected else "NONE"},
                    *([{"op": "replace", "path": "/authorizerId", "value": auth_id}] if protected else [{"op": "remove", "path": "/authorizerId"}])])
        function_arn = f"arn:aws:lambda:{REGION}:000000000000:function:{function}"
        apigw.put_integration(restApiId=api_id, resourceId=rid, httpMethod=method,
            type="AWS_PROXY", integrationHttpMethod="POST",
            uri=f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{function_arn}/invocations")
        ensure_permission(lmb, function, f"apigw-{api_id}-{rid}-{method}", "apigateway.amazonaws.com",
            f"arn:aws:execute-api:{REGION}:000000000000:{api_id}/*/{method}{path}")
        # Minimal unauthenticated MOCK preflight for browser requests.
        try:
            apigw.put_method(restApiId=api_id, resourceId=rid, httpMethod="OPTIONS", authorizationType="NONE")
            apigw.put_integration(restApiId=api_id, resourceId=rid, httpMethod="OPTIONS", type="MOCK",
                requestTemplates={"application/json": '{"statusCode": 200}'})
            apigw.put_method_response(restApiId=api_id, resourceId=rid, httpMethod="OPTIONS", statusCode="200",
                responseParameters={"method.response.header.Access-Control-Allow-Origin": True,
                    "method.response.header.Access-Control-Allow-Headers": True,
                    "method.response.header.Access-Control-Allow-Methods": True})
            apigw.put_integration_response(restApiId=api_id, resourceId=rid, httpMethod="OPTIONS", statusCode="200",
                responseParameters={"method.response.header.Access-Control-Allow-Origin": "'http://localhost:5173'",
                    "method.response.header.Access-Control-Allow-Headers": "'Content-Type,Authorization'",
                    "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,OPTIONS'"})
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("ConflictException", "BadRequestException"):
                raise

    auth_arn = f"arn:aws:lambda:{REGION}:000000000000:function:CareerCloudAuth"
    ensure_permission(lmb, "CareerCloudAuth", f"apigw-{api_id}-authorizer", "apigateway.amazonaws.com",
        f"arn:aws:execute-api:{REGION}:000000000000:{api_id}/authorizers/{auth_id}")
    # Restrict this development role to the tables and resume bucket used by the app.
    iam = aws("iam")
    policy = {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:Scan", "dynamodb:Query"],
         "Resource": [f"arn:aws:dynamodb:{REGION}:000000000000:table/{t}" for t in TABLES]},
        {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject"],
         "Resource": [f"arn:aws:s3:::{BUCKET}/*"]},
        {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"], "Resource": ["*"]}]}
    iam.put_role_policy(RoleName="CareerCloudLambdaRole", PolicyName="CareerCloudLocalDevelopment",
        PolicyDocument=json.dumps(policy))

    resume_arn = f"arn:aws:lambda:{REGION}:000000000000:function:CareerCloudResumeScreening"
    ensure_permission(lmb, "CareerCloudResumeScreening", "s3-resume-upload", "s3.amazonaws.com",
        f"arn:aws:s3:::{BUCKET}")
    s3.put_bucket_notification_configuration(Bucket=BUCKET, NotificationConfiguration={
        "LambdaFunctionConfigurations": [{"LambdaFunctionArn": resume_arn,
            "Events": ["s3:ObjectCreated:*"], "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "resume/"}]}}}]})

    apigw.create_deployment(restApiId=api_id, stageName="dev", description="CareerCloud local development")
    print(json.dumps({"api_id": api_id, "base_url": f"{ENDPOINT}/_aws/execute-api/{api_id}/dev",
        "functions": list(FUNCTIONS), "tables": list(TABLES), "bucket": BUCKET,
        "gemini_key_configured": bool(os.getenv("GEMINI_API_KEY")),
        "auth_secret_generated": True}, indent=2))


if __name__ == "__main__":
    main()
