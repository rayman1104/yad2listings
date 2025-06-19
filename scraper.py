import requests
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
import yad2_parser
from fake_useragent import UserAgent
import random

class VehicleScraper:
    def __init__(self, output_dir, manufacturer, model, price_range=None, km_range=None):
        """
        Initialize the scraper with output directory and vehicle parameters
        
        Args:
            output_dir (str): Directory to save the scraped files
            manufacturer (int): Manufacturer ID
            model (int): Model ID
            price_range (str, optional): Price range in format "min-max" or "-1-max"
            km_range (str, optional): Kilometer range in format "min-max" or "-1-max"
        """
        self.output_dir = Path(output_dir)
        self.manufacturer = manufacturer
        self.model = model
        self.price_range = price_range
        self.km_range = km_range
        self.session = requests.Session()
        self.ua = UserAgent()
        
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
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def get_random_headers(self):
        """Generate random headers for each request"""
        chrome_version = random.choice(self.chrome_versions)
        return {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'dnt': '1',
            'priority': 'u=0, i',
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

    def build_url(self, page_num):
        """Build the URL for a specific page number"""
        base_url = "https://www.yad2.co.il/vehicles/cars"
        params = {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "hand": "0-2",
            "page": page_num
        }
        
        # Add optional parameters if provided
        if self.price_range:
            params["price"] = self.price_range
        if self.km_range:
            params["km"] = self.km_range
            
        return f"{base_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"

    def get_output_filename(self, page_num):
        today = datetime.now().date().strftime("%y_%m_%d")
        """Generate output filename based on manufacturer and model"""
        return self.output_dir / f"{today}_manufacturer{self.manufacturer}_model{self.model}_page{page_num}.html"

    def should_skip_file(self, filepath):
        """Check if file exists and was modified in the last 24 hours"""
        if not filepath.exists():
            return False
            
        file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
        return datetime.now() - file_mtime < timedelta(days=1)

    def fetch_page(self, page_num):
        """
        Fetch a single page and save it to file
        
        Args:
            page_num (int): Page number to fetch
            
        Returns:
            bool: True if page was fetched successfully, False if skipped or failed
        """
        output_file = self.get_output_filename(page_num)
        
        if self.should_skip_file(output_file):
            self.logger.info(f"Skipping page {page_num} - recent file exists")
            with open(output_file, 'r', encoding='utf-8') as file:
                print(f"Processing {output_file}...")
                html_content = file.read()
                data = yad2_parser.extract_json_from_html(html_content)
                listings_data = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']
                return listings_data["pagination"]["pages"]
            
        try:
            url = self.build_url(page_num)
            self.logger.info(f"Fetching page {page_num}")
            
            time.sleep(5)  # Rate limiting
            response = self.session.get(
                url,
                headers=self.get_random_headers(),
                cookies=self.cookies,
                allow_redirects=True
            )
            response.raise_for_status()

            assert len(response.content) > 50000 and b'__NEXT_DATA__' in response.content, len(response.content)
             
            data = yad2_parser.extract_json_from_html(response.content.decode("utf-8"))
            listings_data = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']
            with open(output_file, 'wb') as f:
                f.write(response.content)
                
            self.logger.info(f"Successfully saved page {page_num}")
            return listings_data["pagination"]["pages"]
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching page {page_num}: {str(e)}")
            return

    def scrape_pages(self, max_page=100):
        """
        Fetch multiple pages with rate limiting
        
        Args:
            num_pages (int): Number of pages to fetch
        """
        page = 1
        while True:
            pages = self.fetch_page(page)
            print (f"Page {page}/{pages}")
            # Only wait between requests if we actually made a request
            if pages and page < pages and page < max_page:
                page += 1
            else:
                return

def main():
    # Example usage
    output_dir = "scraped_vehicles"  # Replace with your desired output directory
    # VehicleScraper(output_dir, manufacturer=32, model=1337).scrape_pages() # Nissan
    # return
    VehicleScraper(output_dir, manufacturer=17, model=10182).scrape_pages(max_page=20) # honda civic
    # VehicleScraper(output_dir, manufacturer=32, model=10449).scrape_pages(max_page=20) # Nissan
    # VehicleScraper(output_dir, manufacturer=21, model=10283).scrape_pages(max_page=1) 
    # VehicleScraper(output_dir, manufacturer=41, model=11579).scrape_pages(max_page=5) # ID.4
    # VehicleScraper(output_dir, manufacturer=41, model=12928).scrape_pages(max_page=5) # ID.5
    # VehicleScraper(output_dir, manufacturer=40, model=10545).scrape_pages(max_page=5)
    # VehicleScraper(output_dir, manufacturer=21, model=11239).scrape_pages(max_page=10) # Ioniq 5
    # VehicleScraper(output_dir, manufacturer=92, model=12134).scrape_pages(max_page=10) # Cupra Formentor
    # VehicleScraper(output_dir, manufacturer=41, model=10574).scrape_pages(max_page=10) # Tiguan
    # VehicleScraper(output_dir, manufacturer=40, model=11568).scrape_pages(max_page=10) # Enyaq
    # manufacturer=19&model=10226&subModel=104254,104255,104253
    # VehicleScraper(output_dir, manufacturer=19, model=10226).scrape_pages(max_page=20)
    # scraper = VehicleScraper(output_dir, manufacturer=21, model=10283)
    # scraper = VehicleScraper(output_dir, manufacturer=40, model=10545)
    # scraper = VehicleScraper(output_dir, manufacturer=21, model=11239)
    # scraper = VehicleScraper(output_dir, manufacturer=41, model=10574)

if __name__ == "__main__":
    main()