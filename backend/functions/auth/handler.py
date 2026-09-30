"""LocalStack-friendly account auth and API Gateway token authorizer.

This replaces Cognito for the LocalStack Community workflow. Production AWS
deployments should use Cognito or another managed identity provider.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Attr

TABLE_NAME = os.getenv("USERS_TABLE", "CareerCloudUsers")
REGION = os.getenv("AWS_REGION", "us-east-1")
ENDPOINT = os.getenv("DYNAMODB_ENDPOINT") or os.getenv("AWS_ENDPOINT_URL")
JWT_SECRET = os.getenv("AUTH_SECRET", "")

client_options = {"region_name": REGION}
if ENDPOINT:
    client_options["endpoint_url"] = ENDPOINT
table = boto3.resource("dynamodb", **client_options).Table(TABLE_NAME)


def _b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _json_response(status, body):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
        },
        "body": json.dumps(body),
    }


def _body(event):
    value = event.get("body") or "{}"
    return json.loads(value) if isinstance(value, str) else value


def _issue_token(user):
    if len(JWT_SECRET) < 32:
        raise RuntimeError("Set a random AUTH_SECRET of at least 32 characters on CareerCloudAuth.")
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = _b64(json.dumps({
        "sub": user["userId"],
        "email": user["email"],
        "iat": now,
        "exp": now + 3600,
        "iss": "careercloud-local",
    }, separators=(",", ":")).encode())
    signing_input = f"{header}.{claims}"
    signature = hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def _verify_token(token):
    if len(JWT_SECRET) < 32:
        raise ValueError("AUTH_SECRET is not configured")
    if len(token.split(".")) != 3:
        raise ValueError("Malformed token")
    header, claims, signature = token.split(".")
    encoded_header = json.loads(base64.urlsafe_b64decode(header + "=" * (-len(header) % 4)))
    if encoded_header.get("alg") != "HS256" or encoded_header.get("typ") != "JWT":
        raise ValueError("Unsupported token header")
    signing_input = f"{header}.{claims}"
    expected = _b64(hmac.new(JWT_SECRET.encode(), signing_input.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid token signature")
    payload = json.loads(base64.urlsafe_b64decode(claims + "=" * (-len(claims) % 4)))
    if payload.get("iss") != "careercloud-local" or payload.get("exp", 0) <= int(time.time()):
        raise ValueError("Expired or invalid token")
    return payload


def _public_user(user):
    return {key: value for key, value in user.items() if key not in {"passwordSalt", "passwordHash"}}


def _register(event):
    if len(JWT_SECRET) < 32:
        return _json_response(500, {"message": "Local authentication is not configured."})
    body = _body(event)
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    name = str(body.get("name", "")).strip()
    if not email or not name or len(password) < 10:
        return _json_response(400, {"message": "Name, email, and a password of at least 10 characters are required."})
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    now = datetime.now(timezone.utc).isoformat()
    matches = table.scan(FilterExpression=Attr("email").eq(email)).get("Items", [])
    existing_user = next(iter(matches), None)
    if existing_user and existing_user.get("passwordHash"):
        return _json_response(409, {"message": "An account with this email already exists."})
    if existing_user:
        table.update_item(
            Key={"userId": existing_user["userId"]},
            UpdateExpression="SET passwordSalt = :salt, passwordHash = :hash, updatedAt = :updated",
            ExpressionAttributeValues={":salt": _b64(salt), ":hash": _b64(password_hash), ":updated": now},
        )
        existing_user["passwordSalt"] = _b64(salt)
        existing_user["passwordHash"] = _b64(password_hash)
        return _json_response(201, {"message": "Local account activated.", "user": _public_user(existing_user)})

    user = {
        "userId": str(uuid.uuid4()),
        "email": email,
        "name": name,
        "education": "",
        "skills": [],
        "interests": [],
        "profileComplete": False,
        "passwordSalt": _b64(salt),
        "passwordHash": _b64(password_hash),
        "createdAt": now,
    }
    table.put_item(Item=user, ConditionExpression="attribute_not_exists(userId)")
    return _json_response(201, {"message": "Account created.", "user": _public_user(user)})


def _login(event):
    if len(JWT_SECRET) < 32:
        return _json_response(500, {"message": "Local authentication is not configured."})
    body = _body(event)
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    result = table.scan(FilterExpression=Attr("email").eq(email))
    user = next(iter(result.get("Items", [])), None)
    if not user or not user.get("passwordSalt") or not user.get("passwordHash"):
        return _json_response(401, {"message": "Email or password is incorrect."})
    salt = base64.urlsafe_b64decode(user["passwordSalt"] + "=" * (-len(user["passwordSalt"]) % 4))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    if not hmac.compare_digest(_b64(actual), user["passwordHash"]):
        return _json_response(401, {"message": "Email or password is incorrect."})
    return _json_response(200, {"token": _issue_token(user), "user": _public_user(user)})


def _authorizer(event):
    value = event.get("authorizationToken", "")
    token = value[7:].strip() if value.lower().startswith("bearer ") else value.strip()
    claims = _verify_token(token)
    arn = event["methodArn"]
    parts = arn.split(":")
    api_id, stage = parts[5].split("/")[:2]
    policy_resource = f"{':'.join(parts[:5])}:{api_id}/{stage}/*/*"
    return {
        "principalId": claims["sub"],
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": policy_resource}],
        },
        "context": {"userId": claims["sub"], "email": claims.get("email", "")},
    }


def lambda_handler(event, context):
    if event.get("type") == "TOKEN":
        try:
            return _authorizer(event)
        except Exception as error:
            print("Authorization failed:", str(error))
            raise Exception("Unauthorized") from error

    method = event.get("httpMethod", "")
    path = event.get("path", "")
    if method == "OPTIONS":
        return _json_response(200, {"message": "OK"})
    try:
        if method == "POST" and path.endswith("/auth/register"):
            return _register(event)
        if method == "POST" and path.endswith("/auth/login"):
            return _login(event)
        return _json_response(404, {"message": "Route not found"})
    except Exception as error:
        print("Authentication request failed:", str(error))
        return _json_response(500, {"message": "Unable to complete authentication."})
