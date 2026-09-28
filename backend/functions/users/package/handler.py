import json
import os
import uuid
from datetime import datetime, timezone

import boto3

TABLE_NAME = os.getenv(
    "USERS_TABLE",
    "CareerCloudUsers"
)

DYNAMODB_ENDPOINT = os.getenv(
    "DYNAMODB_ENDPOINT"
) or os.getenv(
    "AWS_ENDPOINT_URL"
)

AWS_REGION = os.getenv(
    "AWS_REGION",
    "us-east-1"
)

dynamodb_kwargs = {
    "region_name": AWS_REGION
}

if DYNAMODB_ENDPOINT:
    dynamodb_kwargs["endpoint_url"] = DYNAMODB_ENDPOINT

dynamodb = boto3.resource(
    "dynamodb",
    **dynamodb_kwargs
)

table = dynamodb.Table(TABLE_NAME)


def create_response(status_code, body):

    return {
        "statusCode": status_code,

        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },

        "body": json.dumps(body)
    }


def create_user(event):

    try:

        body = json.loads(
            event.get("body") or "{}"
        )

        name = body.get("name")
        email = body.get("email")

        if not name or not email:

            return create_response(
                400,
                {
                    "message": "name and email are required"
                }
            )

        user_id = str(uuid.uuid4())

        user = {

            "userId": user_id,

            "name": name,

            "email": email,

            "education": body.get(
                "education",
                ""
            ),

            "skills": body.get(
                "skills",
                []
            ),

            "interests": body.get(
                "interests",
                []
            ),

            "createdAt": datetime.now(
                timezone.utc
            ).isoformat()

        }

        table.put_item(
            Item=user
        )

        return create_response(
            201,
            {
                "message": "User created successfully",
                "user": user
            }
        )

    except Exception as error:

        print(
            "Create user error:",
            str(error)
        )

        return create_response(
            500,
            {
                "message": "Failed to create user",
                "error": str(error)
            }
        )


def get_user(event):

    try:

        path_parameters = (
            event.get("pathParameters")
            or {}
        )

        user_id = path_parameters.get(
            "userId"
        )

        if not user_id:

            return create_response(
                400,
                {
                    "message": "userId is required"
                }
            )

        result = table.get_item(
            Key={
                "userId": user_id
            }
        )

        user = result.get("Item")

        if not user:

            return create_response(
                404,
                {
                    "message": "User not found"
                }
            )

        return create_response(
            200,
            {
                "user": user
            }
        )

    except Exception as error:

        print(
            "Get user error:",
            str(error)
        )

        return create_response(
            500,
            {
                "message": "Failed to get user",
                "error": str(error)
            }
        )


def lambda_handler(event, context):

    print(
        "Received event:",
        json.dumps(event)
    )

    method = event.get(
        "httpMethod",
        ""
    )

    path = event.get(
        "path",
        ""
    )

    if method == "OPTIONS":

        return create_response(
            200,
            {
                "message": "CORS preflight successful"
            }
        )

    if (
        method == "POST"
        and path.endswith("/users")
    ):

        return create_user(event)

    if (
        method == "GET"
        and "/users/" in path
    ):

        return get_user(event)

    return create_response(
        404,
        {
            "message": "Route not found"
        }
    )