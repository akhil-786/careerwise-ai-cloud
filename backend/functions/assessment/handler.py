import json
import os
import uuid
from datetime import datetime, timezone

import boto3


TABLE_NAME = os.getenv(
    "ASSESSMENTS_TABLE",
    "CareerAssessments"
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


def submit_assessment(event):

    try:

        body = json.loads(
            event.get("body") or "{}"
        )

        authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
        claims = authorizer.get("claims") or authorizer.get("jwt", {}).get("claims") or {}
        user_id = authorizer.get("userId") or authorizer.get("principalId") or claims.get("sub")
        answers = body.get("answers")

        if not user_id:
            return create_response(
                401,
                {
                    "message": "Sign in is required."
                }
            )

        if not answers:
            return create_response(
                400,
                {
                    "message": "answers are required"
                }
            )

        assessment_id = str(uuid.uuid4())

        assessment = {

            "assessmentId": assessment_id,

            "userId": user_id,

            "answers": answers,

            "status": "completed",

            "createdAt": datetime.now(
                timezone.utc
            ).isoformat()

        }

        table.put_item(
            Item=assessment
        )

        return create_response(
            201,
            {
                "message": "Assessment submitted successfully",
                "assessment": assessment
            }
        )

    except Exception as error:

        print(
            "Assessment error:",
            str(error)
        )

        return create_response(
            500,
            {
                "message": "Failed to submit assessment",
                "error": str(error)
            }
        )


def lambda_handler(event, context):

    print("Assessment request:", event.get("httpMethod", ""), event.get("path", ""))

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
        and path.endswith("/assessment")
    ):

        return submit_assessment(event)

    return create_response(
        404,
        {
            "message": "Route not found"
        }
    )
