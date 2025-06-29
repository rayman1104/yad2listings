import requests
import time
import os
from datetime import datetime, timedelta
from pathlib import Path
import logging
import yad2_parser
from fake_useragent import UserAgent
import random
from http_utils import http_client

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
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

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

    def fetch_page(self, page_num):
        """
        Fetch a single page and save it to a file
        
        Args:
            page_num (int): Page number to fetch
            
        Returns:
            int: Total number of pages available
        """
        today = datetime.now().date().strftime("%y_%m_%d")
        output_file = self.output_dir / f"page_{page_num}_{today}.html"
        
        try:
            url = self.build_url(page_num)
            self.logger.info(f"Fetching page {page_num}")
            
            time.sleep(5)  # Rate limiting
            
            # Use the centralized HTTP client
            response = http_client.get(url, include_priority=True)

            if not http_client.validate_response(response):
                self.logger.error(f"Invalid response for page {page_num}")
                return None
             
            data = yad2_parser.extract_json_from_html(response.content.decode("utf-8"))
            listings_data = data['props']['pageProps']['dehydratedState']['queries'][0]['state']['data']
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
                
            self.logger.info(f"Successfully saved page {page_num}")
            return listings_data["pagination"]["pages"]
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching page {page_num}: {str(e)}")
            return None

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