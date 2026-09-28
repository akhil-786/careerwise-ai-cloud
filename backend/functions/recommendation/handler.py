import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from google import genai


# ==============================
# Configuration
# ==============================

ASSESSMENTS_TABLE = os.getenv(
    "ASSESSMENTS_TABLE",
    "CareerAssessments"
)

RECOMMENDATIONS_TABLE = os.getenv(
    "RECOMMENDATIONS_TABLE",
    "CareerRecommendations"
)

# Local Windows testing can use DYNAMODB_ENDPOINT.
# LocalStack Lambda can use AWS_ENDPOINT_URL.
DYNAMODB_ENDPOINT = os.getenv(
    "DYNAMODB_ENDPOINT"
) or os.getenv(
    "AWS_ENDPOINT_URL"
)

AWS_REGION = os.getenv(
    "AWS_REGION",
    "us-east-1"
)

GEMINI_API_KEY = ""

# ==============================
# DynamoDB Connection
# ==============================

dynamodb_kwargs = {
    "region_name": AWS_REGION
}

if DYNAMODB_ENDPOINT:
    dynamodb_kwargs["endpoint_url"] = DYNAMODB_ENDPOINT

dynamodb = boto3.resource(
    "dynamodb",
    **dynamodb_kwargs
)

assessment_table = dynamodb.Table(
    ASSESSMENTS_TABLE
)

recommendation_table = dynamodb.Table(
    RECOMMENDATIONS_TABLE
)


# ==============================
# Response Helper
# ==============================

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


# ==============================
# Gemini AI Recommendation
# ==============================

def generate_ai_recommendation(answers):

    if not GEMINI_API_KEY:

        raise ValueError(
            "GEMINI_API_KEY environment variable is not set"
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    prompt = f"""
You are a career guidance assistant.

Analyze the following career assessment scores:

Programming: {answers.get("programming", 0)}/5
Problem Solving: {answers.get("problemSolving", 0)}/5
Cloud Computing: {answers.get("cloud", 0)}/5
Data Science: {answers.get("dataScience", 0)}/5
Web Development: {answers.get("webDevelopment", 0)}/5

Provide a concise career analysis.

Return:

1. Recommended career
2. Why it matches
3. Current strengths
4. Skill gaps
5. A 5-step learning roadmap

Do not claim that the recommendation guarantees a career outcome.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text


# ==============================
# Recommendation Logic
# ==============================

def recommend_career(event):

    try:

        body = json.loads(
            event.get("body") or "{}"
        )

        assessment_id = body.get(
            "assessmentId"
        )

        if not assessment_id:

            return create_response(
                400,
                {
                    "message": "assessmentId is required"
                }
            )

        # ------------------------------
        # Get assessment from DynamoDB
        # ------------------------------

        result = assessment_table.get_item(
            Key={
                "assessmentId": assessment_id
            }
        )

        assessment = result.get("Item")

        if not assessment:

            return create_response(
                404,
                {
                    "message": "Assessment not found"
                }
            )

        answers = assessment.get(
            "answers",
            {}
        )

        # ------------------------------
        # Generate AI recommendation
        # ------------------------------

        ai_recommendation = generate_ai_recommendation(
            answers
        )

        # ------------------------------
        # Create recommendation ID
        # ------------------------------

        recommendation_id = str(
            uuid.uuid4()
        )

        recommendation = {

            "recommendationId":
                recommendation_id,

            "assessmentId":
                assessment_id,

            "userId":
                assessment.get("userId"),

            "recommendation":
                ai_recommendation,

            "createdAt":
                datetime.now(
                    timezone.utc
                ).isoformat()

        }

        # ------------------------------
        # Save recommendation
        # ------------------------------

        recommendation_table.put_item(
            Item=recommendation
        )

        # ------------------------------
        # Return response
        # ------------------------------

        return create_response(
            201,
            {
                "message":
                    "AI career recommendation generated",

                "recommendation":
                    recommendation
            }
        )

    except Exception as error:

        print(
            "Recommendation error:",
            str(error)
        )

        return create_response(
            500,
            {
                "message":
                    "Failed to generate recommendation",

                "error":
                    str(error)
            }
        )


# ==============================
# Lambda Handler
# ==============================

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

    # ------------------------------
    # CORS
    # ------------------------------

    if method == "OPTIONS":

        return create_response(
            200,
            {
                "message":
                    "CORS preflight successful"
            }
        )

    # ------------------------------
    # POST /recommendation
    # ------------------------------

    if (
        method == "POST"
        and path.endswith("/recommendation")
    ):

        return recommend_career(event)

    # ------------------------------
    # Unknown route
    # ------------------------------

    return create_response(
        404,
        {
            "message":
                "Route not found"
        }
    )