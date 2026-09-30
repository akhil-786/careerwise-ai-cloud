import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from google import genai

RECOMMENDATIONS_TABLE = os.getenv(
    "RECOMMENDATIONS_TABLE",
    "CareerRecommendations"
)

ROADMAPS_TABLE = os.getenv(
    "ROADMAPS_TABLE",
    "LearningRoadmaps"
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


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


dynamodb_kwargs = {
    "region_name": AWS_REGION
}

if DYNAMODB_ENDPOINT:
    dynamodb_kwargs["endpoint_url"] = DYNAMODB_ENDPOINT

dynamodb = boto3.resource(
    "dynamodb",
    **dynamodb_kwargs
)

recommendation_table = dynamodb.Table(
    RECOMMENDATIONS_TABLE
)

roadmap_table = dynamodb.Table(
    ROADMAPS_TABLE
)

def create_response(status_code, body):

    return {
        "statusCode": status_code,

        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },

        "body": json.dumps(
            body,
            default=lambda value:
                float(value)
                if isinstance(value, Decimal)
                else str(value)
        )
    }


def generate_roadmap(recommendation):

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set"
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    prompt = f"""
You are a career learning advisor.

Based on the following career recommendation:

{recommendation}

Create a practical personalized learning roadmap.

Return:

1. Target career
2. Skill gaps
3. Learning phases
4. Projects to build
5. Suggested order of learning

Create a roadmap suitable for a college student
with basic programming and cloud knowledge.

Keep it practical and concise.
Do not claim that the roadmap guarantees employment.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


def create_roadmap(event):

    try:

        body = json.loads(
            event.get("body") or "{}"
        )

        recommendation_id = body.get(
            "recommendationId"
        )

        if not recommendation_id:

            return create_response(
                400,
                {
                    "message":
                        "recommendationId is required"
                }
            )

        # Get saved AI recommendation
        result = recommendation_table.get_item(
            Key={
                "recommendationId":
                    recommendation_id
            }
        )

        recommendation = result.get(
            "Item"
        )

        if not recommendation:

            return create_response(
                404,
                {
                    "message":
                        "Recommendation not found"
                }
            )

        authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
        claims = authorizer.get("claims") or authorizer.get("jwt", {}).get("claims") or {}
        user_id = authorizer.get("userId") or authorizer.get("principalId") or claims.get("sub")
        if not user_id:
            return create_response(401, {"message": "Sign in is required."})
        if recommendation.get("userId") != user_id:
            return create_response(403, {"message": "You can only use your own recommendation."})

        # Generate roadmap using Gemini
        roadmap = generate_roadmap(
            recommendation.get(
                "recommendation",
                ""
            )
        )

        roadmap_id = str(
            uuid.uuid4()
        )

        roadmap_record = {

            "roadmapId":
                roadmap_id,

            "recommendationId":
                recommendation_id,

            "userId":
                recommendation.get(
                    "userId"
                ),

            "roadmap":
                roadmap,

            "createdAt":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }

        # Save roadmap
        roadmap_table.put_item(
            Item=roadmap_record
        )

        return create_response(
            201,
            {
                "message":
                    "Learning roadmap generated",

                "roadmap":
                    roadmap_record
            }
        )

    except Exception as error:

        print(
            "Roadmap error:",
            str(error)
        )

        return create_response(
            500,
            {
                "message":
                    "Failed to generate roadmap",

                "error":
                    str(error)
            }
        )


def lambda_handler(event, context):

    print("Roadmap request:", event.get("httpMethod", ""), event.get("path", ""))

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
                "message":
                    "CORS preflight successful"
            }
        )

    if (
        method == "POST"
        and path.endswith("/roadmap")
    ):

        return create_roadmap(event)

    return create_response(
        404,
        {
            "message":
                "Route not found"
        }
    )
