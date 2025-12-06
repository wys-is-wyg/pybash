#!/usr/bin/env python3
"""Quick script to check Leonardo API credits."""

import os
import sys
import requests
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / "app"))

from app.config import settings

def check_credits():
    """Check Leonardo API account info and credits."""
    api_key = settings.LEONARDO_API_KEY
    if not api_key:
        print("ERROR: LEONARDO_API_KEY not set in .env")
        return 1
    
    base_url = settings.LEONARDO_API_BASE_URL
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Try common endpoints for account/credit info
    endpoints = [
        "/users/self",
        "/user",
        "/account",
        "/account/credits",
        "/credits",
    ]
    
    print(f"Checking Leonardo API credits...")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '***'}\n")
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        try:
            print(f"Trying: {endpoint}")
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Success! Response:")
                print(f"  {response.text[:500]}")
                
                # Try to extract credit info
                if isinstance(data, dict):
                    for key in ['credits', 'credit_balance', 'remaining_credits', 'balance', 'user']:
                        if key in data:
                            print(f"\n  Found '{key}': {data[key]}")
                    if 'user' in data and isinstance(data['user'], dict):
                        for key in ['credits', 'credit_balance', 'remaining_credits']:
                            if key in data['user']:
                                print(f"  User credits: {data['user'][key]}")
                
                return 0
            elif response.status_code == 404:
                print(f"  Not found (404)")
            else:
                print(f"  Error: {response.text[:200]}")
        except Exception as e:
            print(f"  Exception: {e}")
        print()
    
    print("Could not find credits endpoint. Check Leonardo API documentation:")
    print("https://docs.leonardo.ai/reference/getuserself")
    return 1

if __name__ == "__main__":
    sys.exit(check_credits())

