

import httpx
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000/api/v1"

def test_create_short_url():
    """Test creating a short URL"""
    
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

def test_get_short_url_by_code():
    create_payload = {
        "original_url": "https://www.github.com",
        "custom_alias": "gh-test",
        "expires_at": None,
        "redirect_type": 302
    }
    
    try:
        create_response = httpx.post(
            f"{BASE_URL}/short-urls",
            json=create_payload,
            timeout=10.0
        )
        
        if create_response.status_code not in [201, 400]:
             print(f"\n✗ Setup failed: Could not create short URL for retrieval test. Status: {create_response.status_code}")
             return

        short_code = "gh-test"
        response = httpx.get(
            f"{BASE_URL}/short-urls/{short_code}",
            timeout=10.0
        )
        
        print(f"\nGet By Short Code Test:")
        print(f"Status Code: {response.status_code}")
        print(f"Response:\n{json.dumps(response.json(), indent=2, default=str)}")
        
        if response.status_code == 200:
            data = response.json()
            if data["short_code"] == short_code:
                print("\n✓ Short URL retrieved successfully!")
            else:
                 print("\n✗ Retrieved data does not match requested short code")
        else:
            print("\n✗ Failed to retrieve short URL")

    except Exception as e:
        print(f"✗ Error: {e}")

def test_redirect():
    create_payload = {
        "original_url": "https://www.python.org",
        "custom_alias": "py-redirect",
        "expires_at": None,
        "redirect_type": 302
    }
    
    try:
        # 1. Create Short URL
        create_response = httpx.post(f"{BASE_URL}/short-urls", json=create_payload, timeout=10.0)
        if create_response.status_code not in [201, 400]: # 400 is ok if it already exists from prev run
             pass

        # 2. Perform Redirect (Root URL)
        # We need to hit the ROOT url, not /api/v1
        ROOT_URL = "http://localhost:8000" 
        short_code = "py-redirect"
        
        # follow_redirects=False allows us to see the 301/302
        response = httpx.get(f"{ROOT_URL}/{short_code}", follow_redirects=False, timeout=10.0)
        
        print(f"\nRedirect Test:")
        print(f"Status Code: {response.status_code}")
        print(f"Location Header: {response.headers.get('location')}")
        
        if response.status_code in [301, 302] and response.headers.get('location') == create_payload['original_url']:
            print("✓ Redirect successful!")
        else:
            print("✗ Redirect failed")
            
        # 3. Verify Click Count
        # Fetch the details from the API to check click_count
        api_response = httpx.get(f"{BASE_URL}/short-urls/{short_code}", timeout=10.0)
        if api_response.status_code == 200:
            data = api_response.json()
            initial_count = 0 # Assuming 0 start
            # If the test ran before, it might be higher.
            # But we just want to see it exists basically.
            print(f"Click Count: {data.get('click_count')}")
            if data.get('click_count') >= 1:
                 print("✓ Click count incremented!")
            else:
                 print("✗ Click count NOT incremented")
        else:
             print("✗ Failed to fetch details for click count verification")
        
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Short URL Creation Endpoint")
    print("=" * 60)
    test_create_short_url()
    test_create_short_url_with_custom_alias()
    test_get_short_url_by_code()
    test_redirect()
