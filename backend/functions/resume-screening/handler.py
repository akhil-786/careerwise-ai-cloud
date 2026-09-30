import os
import json
import uuid
import base64
from io import BytesIO
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote_plus

import boto3
from pypdf import PdfReader
from docx import Document


# ============================================================
# Configuration
# ============================================================

AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

DYNAMODB_ENDPOINT = os.getenv(
    "DYNAMODB_ENDPOINT",
    os.getenv("AWS_ENDPOINT_URL", "")
)

S3_ENDPOINT = os.getenv(
    "S3_ENDPOINT",
    os.getenv("AWS_ENDPOINT_URL", "")
)

S3_PUBLIC_ENDPOINT = os.getenv(
    "S3_PUBLIC_ENDPOINT",
    S3_ENDPOINT
)

RESUME_BUCKET = os.getenv(
    "RESUME_BUCKET",
    "careerwise-resumes"
)

SCREENINGS_TABLE = os.getenv(
    "SCREENINGS_TABLE",
    "ResumeScreenings"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# ============================================================
# AWS Clients
# ============================================================

dynamodb = boto3.resource(
    "dynamodb",
    region_name=AWS_REGION,
    endpoint_url=DYNAMODB_ENDPOINT or None
)

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_ENDPOINT or None
)

s3_presign = boto3.client(
    "s3",
    region_name=AWS_REGION,
    endpoint_url=S3_PUBLIC_ENDPOINT or None
)

table = dynamodb.Table(SCREENINGS_TABLE)


# ============================================================
# Career Profiles
# ============================================================

CAREER_PROFILES = {
    "Cloud Engineer": [
        "AWS",
        "EC2",
        "S3",
        "Lambda",
        "DynamoDB",
        "VPC",
        "CloudWatch",
        "Terraform",
        "Docker",
        "Linux"
    ],

    "DevOps Engineer": [
        "Docker",
        "Kubernetes",
        "CI/CD",
        "Jenkins",
        "GitHub Actions",
        "Terraform",
        "AWS",
        "Linux",
        "Git"
    ],

    "Software Engineer": [
        "Python",
        "Java",
        "JavaScript",
        "React",
        "Node.js",
        "SQL",
        "Git",
        "REST API",
        "MongoDB"
    ],

    "Data Engineer": [
        "Python",
        "SQL",
        "Spark",
        "ETL",
        "AWS",
        "S3",
        "Glue",
        "Redshift",
        "Airflow"
    ],

    "Data Scientist": [
        "Python",
        "Pandas",
        "NumPy",
        "Machine Learning",
        "SQL",
        "Scikit-learn",
        "Statistics",
        "Data Science"
    ]
}


# ============================================================
# Response Helper
# ============================================================

def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "*"
        },
        "body": json.dumps(body)
    }


# ============================================================
# Text Extraction
# ============================================================

def extract_text(file_bytes, file_name):

    extension = Path(file_name).suffix.lower()

    # PDF
    if extension == ".pdf":

        reader = PdfReader(BytesIO(file_bytes))

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""
            pages.append(text)

        return "\n".join(pages)

    # DOCX
    if extension == ".docx":

        document = Document(BytesIO(file_bytes))

        paragraphs = [
            paragraph.text
            for paragraph in document.paragraphs
        ]

        return "\n".join(paragraphs)

    raise ValueError(
        "Unsupported file type. Only PDF and DOCX are supported."
    )


# ============================================================
# Skill Extraction
# ============================================================

def extract_skills(text):

    text_lower = text.lower()

    detected_skills = set()

    all_skills = set()

    for skills in CAREER_PROFILES.values():
        all_skills.update(skills)

    for skill in all_skills:

        if skill.lower() in text_lower:
            detected_skills.add(skill)

    return sorted(detected_skills)


# ============================================================
# Career Matching
# ============================================================

def calculate_career_matches(skills):

    user_skills = {
        skill.lower()
        for skill in skills
    }

    matches = []

    for career, required_skills in CAREER_PROFILES.items():

        matched = []

        for skill in required_skills:

            if skill.lower() in user_skills:
                matched.append(skill)

        percentage = round(
            (len(matched) / len(required_skills)) * 100
        )

        missing = [
            skill
            for skill in required_skills
            if skill.lower() not in user_skills
        ]

        matches.append({
            "career": career,
            "matchPercentage": percentage,
            "matchedSkills": matched,
            "skillGaps": missing[:5]
        })

    matches.sort(
        key=lambda x: x["matchPercentage"],
        reverse=True
    )

    return matches


# ============================================================
# Save Screening Result
# ============================================================

def save_screening(
    screening_id,
    user_id,
    resume_key,
    file_name,
    skills,
    career_matches,
    status
):

    item = {
        "screeningId": screening_id,
        "userId": user_id,
        "resumeKey": resume_key,
        "fileName": file_name,
        "skills": skills,
        "careerMatches": career_matches,
        "status": status,
        "createdAt": datetime.now(
            timezone.utc
        ).isoformat()
    }

    table.put_item(Item=item)

    return item


# ============================================================
# Generate Upload URL
# ============================================================

def generate_upload_url(user_id, file_name):

    screening_id = str(uuid.uuid4())

    safe_file_name = Path(file_name).name

    object_key = (
        f"resume/{user_id}/{screening_id}/{safe_file_name}"
    )

    upload_url = s3_presign.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": RESUME_BUCKET,
            "Key": object_key,
            "ContentType": "application/octet-stream"
        },
        ExpiresIn=900
    )

    table.put_item(
        Item={
            "screeningId": screening_id,
            "userId": user_id,
            "resumeKey": object_key,
            "fileName": safe_file_name,
            "status": "uploaded_pending",
            "createdAt": datetime.now(
                timezone.utc
            ).isoformat()
        }
    )

    return {
        "screeningId": screening_id,
        "resumeKey": object_key,
        "uploadUrl": upload_url
    }


# ============================================================
# Process Resume from S3
# ============================================================

def process_resume_from_s3(
    bucket,
    object_key
):

    object_key = unquote_plus(object_key)

    response_obj = s3.get_object(
        Bucket=bucket,
        Key=object_key
    )

    file_bytes = response_obj["Body"].read()

    file_name = Path(object_key).name

    # Extract text
    text = extract_text(
        file_bytes,
        file_name
    )

    if not text.strip():

        raise ValueError(
            "Could not extract text from resume."
        )

    # Extract skills
    skills = extract_skills(text)

    # Career matching
    career_matches = calculate_career_matches(
        skills
    )

    # Get screening ID from object path
    parts = object_key.split("/")

    screening_id = parts[2]
    user_id = parts[1]

    # Update result
    item = save_screening(
        screening_id=screening_id,
        user_id=user_id,
        resume_key=object_key,
        file_name=file_name,
        skills=skills,
        career_matches=career_matches,
        status="completed"
    )

    return item


# ============================================================
# Get Screening Result
# ============================================================

def get_screening(screening_id):

    result = table.get_item(
        Key={
            "screeningId": screening_id
        }
    )

    item = result.get("Item")

    if not item:
        return None

    return item


def authenticated_user_id(event):
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    claims = authorizer.get("claims") or authorizer.get("jwt", {}).get("claims") or {}
    return authorizer.get("userId") or authorizer.get("principalId") or claims.get("sub")


def process_resume_request(body):
    user_id = body.get("userId")
    screening_id = body.get("screeningId")
    resume_key = body.get("resumeKey")

    if not user_id or not screening_id or not resume_key:
        return response(
            400,
            {
                "message": "userId, screeningId and resumeKey are required"
            }
        )

    try:
        # Make sure the uploaded file belongs to this screening/user
        expected_prefix = f"resume/{user_id}/{screening_id}/"

        if not resume_key.startswith(expected_prefix):
            return response(
                403,
                {
                    "message": "Invalid resume key"
                }
            )

        result = process_resume_from_s3(
            RESUME_BUCKET,
            resume_key
        )

        return response(
            200,
            result
        )

    except Exception as error:

        print(
            "Resume processing error:",
            str(error)
        )

        try:
            table.update_item(
                Key={
                    "screeningId": screening_id
                },
                UpdateExpression="SET #s = :s",
                ExpressionAttributeNames={
                    "#s": "status"
                },
                ExpressionAttributeValues={
                    ":s": "failed"
                }
            )
        except Exception:
            pass

        return response(
            500,
            {
                "message": "Failed to process resume"
            }
        )

# ============================================================
# API Gateway Handler
# ============================================================

def handle_api_request(event):

    method = event.get(
        "httpMethod",
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "")
    )

    path = event.get("path", "")

    # --------------------------------------------------------
    # CORS
    # --------------------------------------------------------

    if method == "OPTIONS":
        return response(
            200,
            {"message": "OK"}
        )

    user_id = authenticated_user_id(event)
    if not user_id:
        return response(401, {"message": "Sign in is required"})

    

    # --------------------------------------------------------
    # POST /resume/upload-url
    # --------------------------------------------------------

    if method == "POST" and path.endswith("/resume/upload-url"):

        body = event.get("body") or "{}"

        if isinstance(body, str):
            body = json.loads(body)

        file_name = body.get("fileName")

        if not file_name:
            return response(
                400,
                {
                    "message":
                    "fileName is required"
                }
            )

        try:

            result = generate_upload_url(
                user_id,
                file_name
            )

            return response(
                200,
                result
            )

        except Exception as error:

            print(
                "Upload URL error:",
                str(error)
            )

            return response(
                500,
                {
                    "message":
                    "Failed to generate upload URL"
                }
            )
        # --------------------------------------------------------
    # POST /resume/process
    # --------------------------------------------------------

    if method == "POST" and path.endswith(
        "/resume/process"
    ):

        body = event.get("body") or "{}"

        if isinstance(body, str):
            body = json.loads(body)

        body["userId"] = user_id

        return process_resume_request(body)
    
    # --------------------------------------------------------
    # GET /resume/{screeningId}
    # --------------------------------------------------------

    if method == "GET":

        screening_id = (
            event.get("pathParameters", {})
            .get("screeningId")
        )

        if screening_id:

            item = get_screening(
                screening_id
            )

            if not item:

                return response(
                    404,
                    {
                        "message":
                        "Screening not found"
                    }
                )

            if item.get("userId") != user_id:
                return response(403, {"message": "You can only view your own screening results"})

            return response(
                200,
                item
            )

    return response(
        404,
        {
            "message":
            "Route not found"
        }
    )


# ============================================================
# Main Lambda Handler
# ============================================================

def lambda_handler(event, context):

    if "Records" in event:
        print("Resume S3 event received")
    else:
        print("Resume API request:", event.get("httpMethod", ""), event.get("path", ""))

    # --------------------------------------------------------
    # S3 Event
    # --------------------------------------------------------

    if "Records" in event:

        results = []

        for record in event["Records"]:

            if record.get(
                "eventSource"
            ) != "aws:s3":

                continue

            bucket = (
                record["s3"]["bucket"]["name"]
            )

            object_key = (
                record["s3"]["object"]["key"]
            )

            try:

                result = process_resume_from_s3(
                    bucket,
                    object_key
                )

                results.append(result)

            except Exception as error:

                print(
                    "Resume processing error:",
                    str(error)
                )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "processed": len(results)
            })
        }

    # --------------------------------------------------------
    # API Gateway
    # --------------------------------------------------------

    return handle_api_request(event)
