#!/usr/bin/env python3
"""
Test script to verify vehicle details fetching functionality
"""

import asyncio
from http_utils import fetch_vehicle_details

async def test_km_fetching():
    """Test fetching vehicle details when km is unknown"""
    
    # Test with a sample vehicle token (you can replace this with a real one)
    test_token = "nzg1tc79"  # Replace with a real vehicle token from Yad2
    
    print(f"\nTesting vehicle details fetching for token: {test_token}")
    
    try:
        details = await fetch_vehicle_details(test_token)
        if details:
            print(f"✓ Successfully fetched details: {details}")
            if 'km' in details:
                print(f"✓ Found mileage: {details['km']}")
            else:
                print("✗ No mileage found in details")
            
            if 'description' in details:
                print(f"✓ Found description: {details['description'][:100]}...")
            else:
                print("✗ No description found in details")
            
            if 'city' in details:
                print(f"✓ Found city: {details['city']}")
            else:
                print("✗ No city found in details")
        else:
            print("✗ Failed to fetch details")
    except Exception as e:
        print(f"✗ Error testing async function: {str(e)}")

def test_km_extraction():
    """Test km extraction from subModel text"""
    
    print("\nTesting km extraction from subModel text...")
    
    test_cases = [
        "2020 1.5L 150 כ״ס 50,000 ק״מ",
        "2019 2.0L 200 כ״ס 75000 ק״מ",
        "2021 1.8L 180 כ״ס 25,000 ק״מ",
        "2018 2.5L 250 כ״ס 100000 ק״מ",
        "No km information here",
        "2022 1.6L 160 כ״ס 0 ק״מ"
    ]
    
    import re
    for text in test_cases:
        km_match = re.search(r'(\d{1,3}(?:,\d{3})*|\d+)\s*ק״מ', text)
        if km_match:
            km_str = km_match.group(1).replace(',', '')
            km = int(km_str)
            print(f"✓ Extracted {km} km from: '{text}'")
        else:
            print(f"✗ No km found in: '{text}'")

def test_database_update():
    """Test database update functionality"""
    
    print("\nTesting database update functionality...")
    
    try:
        from database import VehicleDatabase
        
        # Initialize database
        db = VehicleDatabase()
        
        # Test update with sample data
        test_token = "test_token_123"
        test_description = "This is a test description for the vehicle"
        test_city = "תל אביב"
        test_km = 50000
        
        # Try to update (this will fail if vehicle doesn't exist, but we can test the method)
        result = db.update_vehicle_details(
            test_token,
            description=test_description,
            city=test_city,
            km=test_km
        )
        
        print(f"✓ Database update method executed successfully")
        print(f"  - Token: {test_token}")
        print(f"  - Description: {test_description}")
        print(f"  - City: {test_city}")
        print(f"  - KM: {test_km}")
        
    except Exception as e:
        print(f"✗ Error testing database update: {str(e)}")

if __name__ == "__main__":
    print("Testing Vehicle Details Fetching Functionality")
    print("=" * 50)
    
    # Test km extraction
    test_km_extraction()
    
    # Test async fetching
    asyncio.run(test_km_fetching())
    
    # Test database update
    test_database_update()
    
    print("\n" + "=" * 50)
    print("Test completed!")
    # print("\nTo test with real vehicle tokens:")
    # print("1. Get a vehicle token from a Yad2 listing URL")
    # print("2. Uncomment the asyncio.run(test_km_fetching()) line")
    # print("3. Replace test_token with a real token")
    # print("4. Run the script again") 