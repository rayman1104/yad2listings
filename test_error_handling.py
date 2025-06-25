#!/usr/bin/env python3
"""
Simple test script to verify error handling for missing vehicle fields
"""
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the yad2_parser functions we need
import yad2_parser

def safe_format_date(date_str: str) -> str:
    """Safely format date string, returning empty string if invalid"""
    try:
        if not date_str or date_str.strip() == '':
            return ''
        return yad2_parser.format_date(date_str)
    except Exception as e:
        print(f"Warning: Error formatting date '{date_str}': {str(e)}")
        return ''

def test_vehicle_processing():
    """Test vehicle processing with missing fields"""
    
    # Test vehicle data with missing 'token' field
    test_vehicle_missing_token = {
        'adNumber': 12345,
        'vehicleDates': {
            'yearOfProduction': 2020,
            'monthOfProduction': {'text': 'ינואר'}
        },
        'price': 50000,
        'address': {'city': {'text': 'Tel Aviv'}},
        'adType': 'private',
        'model': {'text': 'Civic'},
        'subModel': {'text': '1.6 120 כ״ס'},
        'manufacturer': {'text': 'Honda'},
        'hand': {'id': 1},
        'dates': {
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z',
            'rebouncedAt': '2024-01-01T00:00:00Z'
        },
        'metaData': {'description': 'Test vehicle'}
    }
    
    # Test vehicle data with missing 'vehicleDates' field
    test_vehicle_missing_dates = {
        'adNumber': 12346,
        'price': 50000,
        'address': {'city': {'text': 'Tel Aviv'}},
        'adType': 'private',
        'model': {'text': 'Civic'},
        'subModel': {'text': '1.6 120 כ״ס'},
        'manufacturer': {'text': 'Honda'},
        'km': 50000,
        'hand': {'id': 1},
        'dates': {
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z',
            'rebouncedAt': '2024-01-01T00:00:00Z'
        },
        'metaData': {'description': 'Test vehicle'},
        'token': 'test-token'
    }
    
    # Test vehicle data with missing 'adNumber' field
    test_vehicle_missing_adnumber = {
        'vehicleDates': {
            'yearOfProduction': 2020,
            'monthOfProduction': {'text': 'ינואר'}
        },
        'price': 50000,
        'address': {'city': {'text': 'Tel Aviv'}},
        'adType': 'private',
        'model': {'text': 'Civic'},
        'subModel': {'text': '1.6 120 כ״ס'},
        'manufacturer': {'text': 'Honda'},
        'km': 50000,
        'hand': {'id': 1},
        'dates': {
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z',
            'rebouncedAt': '2024-01-01T00:00:00Z'
        },
        'metaData': {'description': 'Test vehicle'},
        'token': 'test-token'
    }
    
    # Test valid vehicle data
    test_vehicle_valid = {
        'adNumber': 12347,
        'vehicleDates': {
            'yearOfProduction': 2020,
            'monthOfProduction': {'text': 'ינואר'}
        },
        'price': 50000,
        'address': {'city': {'text': 'Tel Aviv'}},
        'adType': 'private',
        'model': {'text': 'Civic'},
        'subModel': {'text': '1.6 120 כ״ס'},
        'manufacturer': {'text': 'Honda'},
        'km': 50000,
        'hand': {'id': 1},
        'dates': {
            'createdAt': '2024-01-01T00:00:00Z',
            'updatedAt': '2024-01-01T00:00:00Z',
            'rebouncedAt': '2024-01-01T00:00:00Z'
        },
        'metaData': {'description': 'Test vehicle'},
        'token': 'test-token'
    }
    
    test_cases = [
        ("Missing token field", test_vehicle_missing_token),
        ("Missing vehicleDates field", test_vehicle_missing_dates),
        ("Missing adNumber field", test_vehicle_missing_adnumber),
        ("Valid vehicle", test_vehicle_valid)
    ]
    
    print("Testing vehicle processing error handling...")
    print("=" * 50)
    
    for test_name, vehicle_data in test_cases:
        print(f"\nTesting: {test_name}")
        try:
            # Check for essential fields first
            if 'token' not in vehicle_data:
                print("  ❌ Skipping vehicle without token")
                continue
            
            if 'vehicleDates' not in vehicle_data:
                print(f"  ❌ Skipping vehicle {vehicle_data.get('token', 'unknown')} without vehicleDates")
                continue
            
            # Process the vehicle
            year = vehicle_data['vehicleDates']['yearOfProduction']
            month = yad2_parser.get_month_number(
                vehicle_data['vehicleDates'].get('monthOfProduction', {"text": "ינואר"})['text']
            )
            production_date = f"{year}-{month:02d}-01"
            
            years_since_production = yad2_parser.calculate_years_since_production(year, month)
            
            # Handle missing km field
            km = vehicle_data.get('km', 0)
            km_per_year = round(km / years_since_production if years_since_production > 0 else km, 2)
            
            # Extract HP from subModel text
            submodel_text = vehicle_data.get('subModel', {}).get('text', '')
            hp_match = re.search(r'(\d+)\s*כ״ס', submodel_text)
            hp = int(hp_match.group(1)) if hp_match else 0
            
            processed_vehicle = {
                'token': vehicle_data['token'],  # Use token as primary key
                'adNumber': vehicle_data.get('adNumber', ''),  # Keep for backward compatibility
                'price': vehicle_data.get('price', 0),
                'city': vehicle_data.get('address', {}).get('city', {"text": ""})['text'],
                'adType': vehicle_data.get('adType', ''),
                'model': vehicle_data.get('model', {}).get('text', ''),
                'subModel': submodel_text,
                'hp': hp,
                'make': vehicle_data.get('manufacturer', {}).get('text', ''),
                'productionDate': production_date,
                'km': km,
                'hand': vehicle_data.get('hand', {}).get('id', 0),
                'createdAt': safe_format_date(vehicle_data.get('dates', {}).get('createdAt', '')),
                'updatedAt': safe_format_date(vehicle_data.get('dates', {}).get('updatedAt', '')),
                'rebouncedAt': safe_format_date(vehicle_data.get('dates', {}).get('rebouncedAt', '')),
                'listingType': 'test',
                'number_of_years': years_since_production,
                'km_per_year': km_per_year,
                'description': vehicle_data.get("metaData", {}).get("description", ''),
                'link': f'https://www.yad2.co.il/vehicles/item/{vehicle_data.get("token", "")}',
            }
            
            print(f"  ✅ Successfully processed vehicle {processed_vehicle['token']}")
            print(f"     KM: {processed_vehicle['km']}")
            print(f"     HP: {processed_vehicle['hp']}")
            print(f"     Price: {processed_vehicle['price']}")
            print(f"     City: {processed_vehicle['city']}")
            
        except Exception as e:
            print(f"  ❌ Error processing vehicle: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_vehicle_processing() 