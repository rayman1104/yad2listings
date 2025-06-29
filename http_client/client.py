import requests
import random
import logging
from typing import Dict, Optional
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class Yad2HttpClient:
    """Centralized HTTP client for Yad2 requests with shared headers and cookies"""
    
    def __init__(self):
        # List of Chrome versions to randomize from
        self.chrome_versions = ["137.0.0.0", "136.0.0.0", "135.0.0.0", "134.0.0.0"]
        
        # Set up cookies
        self.cookies = {
            '__ssds': '3',
            'y2018-2-cohort': '43',
            'cohortGroup': 'C',
            'abTestKey': '15',
            '__uzma': '55da8501-f247-4a91-8a57-19c75987e296',
            '__uzmb': '1749975893',
            '__uzme': '6903',
            '__ssuzjsr3': 'a9be0cd8e',
            '__uzmaj3': '355eedea-b2ed-4c02-92ec-8dbc842b2fc2',
            '__uzmbj3': '1749975894',
            '__uzmlj3': 'tafY2FdZcjkgEC0K5j4s/f7RYtYhe/AhsioVyGyyTis=',
            'guest_token': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwYXlsb2FkIjp7InV1aWQiOiIxMTE3YWYwYS0yNDVlLTQxYzctOTg5Ni1iYzRlNmI2OTVlODcifSwiaWF0IjoxNzQ5OTc1ODk1LCJleHAiOjE3ODE1MzM0OTV9.aPPuJzDg7kGA5oshucuzEeGb99H09sCzdXZKR3Je_Rg',
            'recommendations-home-category': '{"categoryId":1,"subCategoryId":21}',
            'ab.storage.deviceId.716d3f2d-2039-4ea6-bd67-0782ecd0770b': 'g%3Ab60a4504-2f28-cdc6-e49b-3afb63388151%7Ce%3Aundefined%7Cc%3A1749975895194%7Cl%3A1750276630445',
            'ab.storage.sessionId.716d3f2d-2039-4ea6-bd67-0782ecd0770b': 'g%3A1996d7c1-6c54-2a4d-e158-c729f0a26cfb%7Ce%3A1750280714203%7Cc%3A1750276630445%7Cl%3A1750278914203',
            '__uzmcj3': '2413814212675',
            '__uzmdj3': '1750278914',
            '__uzmfj3': '7f60009709b3d1-eafe-4ff9-a1fc-9e818d8e16071749975894222303020158-ec8e9d5c6f4125d4142',
            '__uzmd': '1750278921',
            '__uzmc': '5841822693326',
            '__uzmf': '7f60009709b3d1-eafe-4ff9-a1fc-9e818d8e16071749975893057303028360-8c04c88bb204e1aa226',
            'uzmx': '7f900054e51021-3353-49b3-8035-06cb5dd2de064-1749975893057303028360-47282bc20cff04dd469'
        }
    
    def get_random_headers(self, include_priority: bool = False) -> Dict[str, str]:
        """Generate random headers for each request"""
        chrome_version = random.choice(self.chrome_versions)
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'dnt': '1',
            'sec-ch-ua': f'"Chromium";v="{chrome_version.split(".")[0]}", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36'
        }
        
        if include_priority:
            headers['priority'] = 'u=0, i'
            
        return headers
    
    def create_session(self) -> requests.Session:
        """Create a new requests session with default configuration"""
        session = requests.Session()
        return session
    
    def get(self, url: str, timeout: int = 10, include_priority: bool = False) -> requests.Response:
        """Make a GET request with standard headers and cookies"""
        session = self.create_session()
        headers = self.get_random_headers(include_priority)
        
        response = session.get(
            url,
            headers=headers,
            cookies=self.cookies,
            allow_redirects=True,
            timeout=timeout
        )
        response.raise_for_status()
        return response
    
    def validate_response(self, response: requests.Response, min_content_length: int = 50000) -> bool:
        """Validate that the response contains expected content"""
        return (len(response.content) >= min_content_length and 
                b'__NEXT_DATA__' in response.content)

# Global instance for easy access
http_client = Yad2HttpClient()

async def fetch_vehicle_details(vehicle_token: str) -> Dict:
    """Fetch detailed vehicle information from individual vehicle page"""
    try:
        vehicle_url = f"https://www.yad2.co.il/vehicles/item/{vehicle_token}"
        
        response = http_client.get(vehicle_url, timeout=10)
        
        if not http_client.validate_response(response):
            logger.warning(f"Invalid response for vehicle {vehicle_token}")
            return {}
        
        # Parse the data
        from parser import extract_json_from_html
        data = extract_json_from_html(response.content.decode("utf-8"))
        
        # Extract vehicle details from the page
        vehicle_data = data.get('props', {}).get('pageProps', {}).get('dehydratedState', {}).get('queries', [])
        
        if not vehicle_data:
            logger.warning(f"No vehicle data found for {vehicle_token}")
            return {}
        
        # Look for vehicle details in the queries
        vehicle_details = {}
        for query in vehicle_data:
            if 'state' in query and 'data' in query['state']:
                data_item = query['state']['data']
                if isinstance(data_item, dict):
                    # Look for vehicle data that contains km or other vehicle fields
                    if 'km' in data_item or 'description' in data_item or 'address' in data_item:
                        vehicle_details = data_item
                        break
        
        if not vehicle_details:
            logger.warning(f"No vehicle details found for {vehicle_token}")
            return {}
        
        # Extract specific fields we need
        result = {}
        
        # Extract km
        if 'km' in vehicle_details:
            result['km'] = vehicle_details['km']
        
        # Extract description - try different possible locations
        description = None
        if 'description' in vehicle_details:
            description = vehicle_details['description']
        elif 'metaData' in vehicle_details and 'description' in vehicle_details['metaData']:
            description = vehicle_details['metaData']['description']
        
        if description:
            result['description'] = description
        
        # Extract city/location - try different possible locations
        city = None
        if 'address' in vehicle_details:
            address = vehicle_details['address']
            if isinstance(address, dict):
                if 'area' in address and 'text' in address['area']:
                    city = address['area']['text']
                elif 'city' in address and 'text' in address['city']:
                    city = address['city']['text']
                elif 'text' in address:
                    city = address['text']
        elif 'city' in vehicle_details:
            city_data = vehicle_details['city']
            if isinstance(city_data, dict) and 'text' in city_data:
                city = city_data['text']
            elif isinstance(city_data, str):
                city = city_data
        
        if city:
            result['city'] = city
        
        logger.info(f"Successfully fetched details for vehicle {vehicle_token}: {list(result.keys())}")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching vehicle details for {vehicle_token}: {str(e)}")
        return {} 