import boto3

client = boto3.client(
    "apigateway",
    endpoint_url="http://localhost:4566",
    region_name="us-east-1",
    aws_access_key_id="test",
    aws_secret_access_key="test",
)

api_id = "oj5llvuszk"
resource_id = "h4g8vgbyzo"

# Create the 200 method response
client.put_method_response(
    restApiId=api_id,
    resourceId=resource_id,
    httpMethod="OPTIONS",
    statusCode="200",
    responseParameters={
        "method.response.header.Access-Control-Allow-Origin": True,
        "method.response.header.Access-Control-Allow-Headers": True,
        "method.response.header.Access-Control-Allow-Methods": True,
    },
)

# Configure the actual CORS headers
client.put_integration_response(
    restApiId=api_id,
    resourceId=resource_id,
    httpMethod="OPTIONS",
    statusCode="200",
    responseParameters={
        "method.response.header.Access-Control-Allow-Origin": "'*'",
        "method.response.header.Access-Control-Allow-Headers": "'Content-Type'",
        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
    },
)

print("CORS response configured successfully")