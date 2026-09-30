import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr

REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT = os.getenv("DYNAMODB_ENDPOINT") or os.getenv("AWS_ENDPOINT_URL")
TABLE_NAMES = {
    "users": os.getenv("USERS_TABLE", "CareerCloudUsers"),
    "assessments": os.getenv("ASSESSMENTS_TABLE", "CareerAssessments"),
    "recommendations": os.getenv("RECOMMENDATIONS_TABLE", "CareerRecommendations"),
    "roadmaps": os.getenv("ROADMAPS_TABLE", "LearningRoadmaps"),
    "screenings": os.getenv("SCREENINGS_TABLE", "ResumeScreenings"),
}

options = {"region_name": REGION}
if ENDPOINT:
    options["endpoint_url"] = ENDPOINT
dynamodb = boto3.resource("dynamodb", **options)
tables = {key: dynamodb.Table(name) for key, name in TABLE_NAMES.items()}


def _serialize(value):
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
        },
        "body": json.dumps(body, default=_serialize),
    }


def authenticated_user_id(event):
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    claims = authorizer.get("claims") or authorizer.get("jwt", {}).get("claims") or {}
    return authorizer.get("userId") or authorizer.get("principalId") or claims.get("sub")


def _safe_user(user):
    if not user:
        return None
    return {key: value for key, value in user.items() if key not in {"passwordSalt", "passwordHash"}}


def _body(event):
    body = event.get("body") or "{}"
    return json.loads(body) if isinstance(body, str) else body


def create_user(event):
    user_id = authenticated_user_id(event)
    if not user_id:
        return response(401, {"message": "Sign in is required."})
    body = _body(event)
    name = str(body.get("name", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    if not name or not email:
        return response(400, {"message": "name and email are required"})
    now = datetime.now(timezone.utc).isoformat()
    existing = tables["users"].get_item(Key={"userId": user_id}).get("Item") or {}
    user = {
        **existing,
        "userId": user_id,
        "name": name,
        "email": email,
        "education": str(body.get("education", "")).strip(),
        "skills": body.get("skills", []),
        "interests": body.get("interests", []),
        "profileComplete": True,
        "updatedAt": now,
    }
    user.setdefault("createdAt", now)
    tables["users"].put_item(Item=user)
    return response(200, {"message": "Profile saved", "user": _safe_user(user)})


def get_user(event):
    user_id = (event.get("pathParameters") or {}).get("userId")
    caller_id = authenticated_user_id(event)
    if not caller_id:
        return response(401, {"message": "Sign in is required."})
    if not user_id or user_id != caller_id:
        return response(403, {"message": "You can only access your own profile."})
    user = tables["users"].get_item(Key={"userId": user_id}).get("Item")
    if not user:
        return response(404, {"message": "User not found"})
    return response(200, {"user": _safe_user(user)})


def update_skills(event):
    user_id = (event.get("pathParameters") or {}).get("userId")
    caller_id = authenticated_user_id(event)
    if not caller_id:
        return response(401, {"message": "Sign in is required."})
    if user_id != caller_id:
        return response(403, {"message": "You can only update your own skills."})
    body = _body(event)
    skills = body.get("skills")
    if not isinstance(skills, list) or any(not isinstance(item, str) or not item.strip() for item in skills):
        return response(400, {"message": "skills must be a list of non-empty strings"})
    normalized = sorted({skill.strip() for skill in skills})
    result = tables["users"].update_item(
        Key={"userId": user_id},
        UpdateExpression="SET skills = :skills, updatedAt = :updated",
        ExpressionAttributeValues={
            ":skills": normalized,
            ":updated": datetime.now(timezone.utc).isoformat(),
        },
        ReturnValues="ALL_NEW",
    )
    return response(200, {"user": _safe_user(result["Attributes"])})


def _scan_user_records(table, user_id):
    records = []
    scan_options = {"FilterExpression": Attr("userId").eq(user_id)}
    while True:
        result = table.scan(**scan_options)
        records.extend(result.get("Items", []))
        last_key = result.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_options["ExclusiveStartKey"] = last_key
    return sorted(records, key=lambda item: item.get("createdAt", ""), reverse=True)


def dashboard(event):
    user_id = (event.get("pathParameters") or {}).get("userId")
    caller_id = authenticated_user_id(event)
    if not caller_id:
        return response(401, {"message": "Sign in is required."})
    if user_id != caller_id:
        return response(403, {"message": "You can only view your own dashboard."})
    user = tables["users"].get_item(Key={"userId": user_id}).get("Item")
    if not user:
        return response(404, {"message": "User profile not found"})
    history = {
        name: _scan_user_records(tables[name], user_id)
        for name in ("assessments", "recommendations", "roadmaps", "screenings")
    }
    return response(200, {"user": _safe_user(user), **history})


def lambda_handler(event, context):
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    if method == "OPTIONS":
        return response(200, {"message": "OK"})
    if method == "POST" and path.endswith("/users"):
        return create_user(event)
    if method == "GET" and "/dashboard/" in path:
        return dashboard(event)
    if method == "PUT" and path.endswith("/skills"):
        return update_skills(event)
    if method == "GET" and "/users/" in path:
        return get_user(event)
    return response(404, {"message": "Route not found"})
