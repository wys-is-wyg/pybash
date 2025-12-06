#!/bin/bash
# Quick script to check Leonardo API credits

cd "$(dirname "$0")"

# Load API key from .env
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep LEONARDO_API_KEY | xargs)
fi

if [ -z "$LEONARDO_API_KEY" ]; then
    echo "ERROR: LEONARDO_API_KEY not found in .env"
    exit 1
fi

echo "Checking Leonardo API credits..."
echo "API Key: ${LEONARDO_API_KEY:0:8}...${LEONARDO_API_KEY: -4}"
echo ""

# Try multiple endpoints
endpoints=(
    "/me"
    "/users/me"
    "/user/me"
    "/account"
    "/account/balance"
    "/credits"
    "/user"
)

for endpoint in "${endpoints[@]}"; do
    echo "Trying: https://cloud.leonardo.ai/api/rest/v1$endpoint"
    response=$(curl -s -w "\n%{http_code}" \
        -X GET "https://cloud.leonardo.ai/api/rest/v1$endpoint" \
        -H "Authorization: Bearer $LEONARDO_API_KEY" \
        -H 'Content-Type: application/json')
    
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ]; then
        echo "✓ Success! HTTP Status: $http_code"
        echo ""
        echo "Response:"
        echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
        
        # Try to extract credits/tokens if present
        echo ""
        echo "=== Account Information ==="
        echo "$response_body" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'user_details' in data and len(data['user_details']) > 0:
        user = data['user_details'][0]
        print(f\"User: {user.get('user', {}).get('username', 'N/A')}\")
        print(f\"Subscription Tokens: {user.get('subscriptionTokens', 0)}\")
        print(f\"API Subscription Tokens: {user.get('apiSubscriptionTokens', 0)}\")
        print(f\"Paid Tokens: {user.get('paidTokens', 0)}\")
        if 'tokenRenewalDate' in user:
            print(f\"Token Renewal Date: {user['tokenRenewalDate']}\")
        if 'apiPlanTokenRenewalDate' in user:
            print(f\"API Plan Token Renewal: {user['apiPlanTokenRenewalDate']}\")
        total = user.get('subscriptionTokens', 0) + user.get('apiSubscriptionTokens', 0) + user.get('paidTokens', 0)
        print(f\"\nTotal Available Tokens: {total}\")
    else:
        # Try direct fields
        print(f\"Subscription Tokens: {data.get('subscriptionTokens', 'N/A')}\")
        print(f\"API Subscription Tokens: {data.get('apiSubscriptionTokens', 'N/A')}\")
except Exception as e:
    print(f\"Error parsing response: {e}\")
" 2>/dev/null || echo "Could not parse credits from response"
        exit 0
    else
        echo "  Status: $http_code"
    fi
    echo ""
done

# If all endpoints failed, try the original one and show error
echo "Trying: https://cloud.leonardo.ai/api/rest/v1/users/self"
response=$(curl -s -w "\n%{http_code}" \
    -X GET 'https://cloud.leonardo.ai/api/rest/v1/users/self' \
    -H "Authorization: Bearer $LEONARDO_API_KEY" \
    -H 'Content-Type: application/json')

# Split response body and status code
http_code=$(echo "$response" | tail -n1)
response_body=$(echo "$response" | sed '$d')

echo "HTTP Status: $http_code"
echo ""

if [ "$http_code" = "200" ]; then
    echo "Response:"
    echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
    
    # Try to extract credits if present
    credits=$(echo "$response_body" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('credits', data.get('credit_balance', data.get('remaining_credits', data.get('balance', 'N/A')))))" 2>/dev/null)
    if [ "$credits" != "N/A" ] && [ -n "$credits" ]; then
        echo ""
        echo "=== Credits Remaining: $credits ==="
    fi
else
    echo "Error response:"
    echo "$response_body"
    echo ""
    echo "Note: Leonardo API may not expose credits via REST API."
    echo "Check your dashboard at: https://app.leonardo.ai/"
fi

