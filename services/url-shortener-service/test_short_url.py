#!/usr/bin/env python
"""
Test script to create a short URL via the FastAPI endpoint.
Run the FastAPI app first with: uvicorn app.main:app --reload
"""

import httpx
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_create_short_url():
    """Test creating a short URL"""
    
    # Prepare the request payload
    payload = {
        "original_url": "https://www.example.com/very/long/url/that/needs/shortening",
        "custom_alias": None,  # Leave as None for auto-generated code
        "expires_at": None,
        "redirect_type": 302
    }
    
    try:
        response = httpx.post(
            f"{BASE_URL}/short-urls",
            json=payload,
            timeout=10.0
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 201:
            print("\n✓ Short URL created successfully!")
        else:
            print("\n✗ Failed to create short URL")
            
    except httpx.ConnectError:
        print("✗ Connection error. Make sure the FastAPI app is running:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"✗ Error: {e}")

def test_create_short_url_with_custom_alias():
    """Test creating a short URL with custom alias"""
    
    payload = {
        "original_url": "https://www.google.com",
        "custom_alias": "my-search",
        "expires_at": None,
        "redirect_type": 301
    }
    
    try:
        response = httpx.post(
            f"{BASE_URL}/short-urls",
            json=payload,
            timeout=10.0
        )
        
        print(f"\nCustom Alias Test:")
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 201:
            print("\n✓ Short URL with custom alias created successfully!")
        else:
            print("\n✗ Failed to create short URL with custom alias")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Short URL Creation Endpoint")
    print("=" * 60)
    test_create_short_url()
    test_create_short_url_with_custom_alias()
