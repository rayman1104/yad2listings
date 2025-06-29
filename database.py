import psycopg2
import psycopg2.extras
from datetime import datetime
import os
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

class VehicleDatabase:
    def __init__(self, database_url: str = None):
        """
        Initialize database connection
        
        Args:
            database_url: PostgreSQL connection URL or use DATABASE_URL env var
        """
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        
        self.create_tables()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def create_tables(self):
        """Create necessary tables if they don't exist (using migrations)"""
        try:
            from migrations import MigrationRunner
            migration_runner = MigrationRunner(self.database_url)
            migration_runner.run_all_migrations()
            logger.info("Database tables created/verified successfully via migrations")
        except ImportError:
            # Fallback to direct table creation if migrations module not available
            logger.warning("Migrations module not available, using direct table creation")
            self._create_tables_directly()
    
    def _create_tables_directly(self):
        """Direct table creation as fallback"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Create vehicles table with JSONB approach
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS vehicles (
                        token TEXT PRIMARY KEY,
                        manufacturer_id INTEGER NOT NULL,
                        model_id INTEGER NOT NULL,
                        price INTEGER,
                        city TEXT,
                        vehicle_data JSONB NOT NULL,
                        first_seen TIMESTAMP DEFAULT NOW(),
                        last_seen TIMESTAMP DEFAULT NOW(),
                        is_sent BOOLEAN DEFAULT FALSE
                    )
                """)
                
                # Essential indexes for performance
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_token 
                    ON vehicles (token)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_manufacturer_model 
                    ON vehicles (manufacturer_id, model_id)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_first_seen 
                    ON vehicles (first_seen)
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_is_sent 
                    ON vehicles (is_sent)
                """)
                
                # JSONB indexes for common queries
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_price_range 
                    ON vehicles USING GIN ((vehicle_data->'price'))
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_production_year 
                    ON vehicles USING GIN ((vehicle_data->'productionDate'))
                """)
                
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_km 
                    ON vehicles USING GIN ((vehicle_data->'km'))
                """)
                
                # General JSONB index for other queries
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_vehicles_data 
                    ON vehicles USING GIN (vehicle_data)
                """)
                
                conn.commit()
                logger.info("Database tables created/verified successfully")
    
    def _prepare_vehicle_data(self, vehicle: Dict) -> Dict:
        """Prepare vehicle data for JSONB storage"""
        # Extract main fields
        token = vehicle.get('token', '')
        if not token:
            # Fallback to adNumber if token is not available
            token = str(vehicle.get('adNumber', ''))
        
        price = vehicle.get('price')
        city = vehicle.get('city', '')
        
        # Prepare JSONB data with all other fields
        vehicle_data = {
            'adNumber': vehicle.get('adNumber'),  # Keep for backward compatibility
            'token': token,  # Store token in JSONB as well
            'adType': vehicle.get('adType'),
            'model': vehicle.get('model'),
            'subModel': vehicle.get('subModel'),
            'hp': vehicle.get('hp'),
            'make': vehicle.get('make'),
            'productionDate': vehicle.get('productionDate'),
            'km': vehicle.get('km'),
            'hand': vehicle.get('hand'),
            'createdAt': vehicle.get('createdAt'),
            'updatedAt': vehicle.get('updatedAt'),
            'rebouncedAt': vehicle.get('rebouncedAt'),
            'listingType': vehicle.get('listingType'),
            'number_of_years': vehicle.get('number_of_years'),
            'km_per_year': vehicle.get('km_per_year'),
            'description': vehicle.get('description'),
            'link': vehicle.get('link'),
            'price': price,  # Duplicated for JSONB queries
        }
        
        # Remove None values to keep JSONB clean
        vehicle_data = {k: v for k, v in vehicle_data.items() if v is not None}
        
        return token, price, city, vehicle_data
    
    def save_vehicles(self, vehicles_data: List[Dict], manufacturer_id: int, model_id: int) -> List[Dict]:
        """
        Save vehicles to database and return new vehicles
        
        Args:
            vehicles_data: List of vehicle dictionaries from yad2_parser
            manufacturer_id: Manufacturer ID
            model_id: Model ID
            
        Returns:
            List of new vehicles that weren't in database before
        """
        new_vehicles = []
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                for vehicle in vehicles_data:
                    try:
                        token, price, city, vehicle_data = self._prepare_vehicle_data(vehicle)
                        
                        # Check if vehicle already exists
                        cur.execute(
                            "SELECT token, first_seen FROM vehicles WHERE token = %s",
                            (token,)
                        )
                        existing = cur.fetchone()
                        
                        if existing:
                            # Update last_seen timestamp and vehicle_data
                            cur.execute("""
                                UPDATE vehicles 
                                SET last_seen = NOW(), 
                                    vehicle_data = %s,
                                    price = %s,
                                    city = %s
                                WHERE token = %s
                            """, (psycopg2.extras.Json(vehicle_data), price, city, token))
                        else:
                            # Insert new vehicle
                            cur.execute("""
                                INSERT INTO vehicles (
                                    token, manufacturer_id, model_id, price, city,
                                    vehicle_data, first_seen, last_seen
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, NOW(), NOW()
                                )
                            """, (token, manufacturer_id, model_id, price, city, 
                                  psycopg2.extras.Json(vehicle_data)))
                            
                            # Create a full vehicle dict for backward compatibility
                            full_vehicle = {'token': token, 'price': price, 'city': city, **vehicle_data}
                            new_vehicles.append(full_vehicle)
                            logger.info(f"New vehicle added: {token}")
                    
                    except Exception as e:
                        logger.error(f"Error saving vehicle {vehicle.get('token', 'unknown')}: {str(e)}")
                        continue
                
                conn.commit()
        
        logger.info(f"Processed {len(vehicles_data)} vehicles, found {len(new_vehicles)} new ones")
        return new_vehicles
    
    def mark_as_sent(self, tokens: List[str]):
        """Mark vehicles as sent to avoid sending duplicates"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE vehicles SET is_sent = TRUE WHERE token = ANY(%s)",
                    (tokens,)
                )
                conn.commit()
                logger.info(f"Marked {len(tokens)} vehicles as sent")
    
    def update_vehicle_details(self, token: str, description: str = None, city: str = None, km: int = None):
        """Update vehicle details after fetching from individual page"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                update_parts = []
                params = []
                
                if description is not None:
                    update_parts.append("vehicle_data = jsonb_set(vehicle_data, '{description}', %s)")
                    params.append(json.dumps(description))
                
                if city is not None:
                    update_parts.append("city = %s")
                    params.append(city)
                
                if km is not None:
                    update_parts.append("vehicle_data = jsonb_set(vehicle_data, '{km}', %s)")
                    params.append(json.dumps(km))
                
                if update_parts:
                    params.append(token)
                    query = f"""
                        UPDATE vehicles 
                        SET {', '.join(update_parts)}
                        WHERE token = %s
                    """
                    cur.execute(query, params)
                    conn.commit()
                    logger.info(f"Updated details for vehicle {token}")
                    return True
                
                return False
    
    def get_unsent_vehicles(self, manufacturer_id: int = None, model_id: int = None, limit: int = 10) -> List[Dict]:
        """Get vehicles that haven't been sent yet"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                query = """
                    SELECT token, price, city, vehicle_data, first_seen, last_seen, is_sent
                    FROM vehicles 
                    WHERE is_sent = FALSE
                """
                params = []
                
                if manufacturer_id:
                    query += " AND manufacturer_id = %s"
                    params.append(manufacturer_id)
                
                if model_id:
                    query += " AND model_id = %s"
                    params.append(model_id)
                
                query += " ORDER BY first_seen DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Flatten the results for backward compatibility
                flattened_results = []
                for row in results:
                    flattened = dict(row['vehicle_data'])
                    flattened.update({
                        'token': row['token'],
                        'first_seen': row['first_seen'],
                        'last_seen': row['last_seen'],
                        'is_sent': row['is_sent']
                    })
                    flattened_results.append(flattened)
                
                return flattened_results
    
    def get_vehicle_stats(self) -> Dict:
        """Get database statistics"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_vehicles,
                        COUNT(*) FILTER (WHERE is_sent = FALSE) as unsent_vehicles,
                        COUNT(DISTINCT manufacturer_id) as unique_manufacturers,
                        COUNT(DISTINCT model_id) as unique_models,
                        MIN(first_seen) as oldest_entry,
                        MAX(first_seen) as newest_entry
                    FROM vehicles
                """)
                return dict(cur.fetchone())
    
    def cleanup_old_vehicles(self, days_old: int = 30):
        """Remove vehicles older than specified days"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM vehicles WHERE first_seen < NOW() - INTERVAL '{days_old} days'"
                )
                deleted_count = cur.rowcount
                conn.commit()
                logger.info(f"Deleted {deleted_count} vehicles older than {days_old} days")
                return deleted_count
    
    def search_vehicles(self, filters: Dict, limit: int = 50) -> List[Dict]:
        """
        Advanced search using JSONB capabilities
        
        Example filters:
        {
            'price_min': 50000,
            'price_max': 150000,
            'km_max': 100000,
            'production_year_min': 2018,
            'make': 'Toyota',
            'city': 'תל אביב'
        }
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = []
                params = []
                param_count = 0
                
                # Price range
                if 'price_min' in filters:
                    param_count += 1
                    conditions.append(f"(vehicle_data->>'price')::integer >= ${param_count}")
                    params.append(filters['price_min'])
                
                if 'price_max' in filters:
                    param_count += 1
                    conditions.append(f"(vehicle_data->>'price')::integer <= ${param_count}")
                    params.append(filters['price_max'])
                
                # KM range
                if 'km_max' in filters:
                    param_count += 1
                    conditions.append(f"(vehicle_data->>'km')::integer <= ${param_count}")
                    params.append(filters['km_max'])
                
                # Production year
                if 'production_year_min' in filters:
                    param_count += 1
                    conditions.append(f"EXTRACT(YEAR FROM (vehicle_data->>'productionDate')::date) >= ${param_count}")
                    params.append(filters['production_year_min'])
                
                # Exact matches
                if 'make' in filters:
                    param_count += 1
                    conditions.append(f"vehicle_data->>'make' = ${param_count}")
                    params.append(filters['make'])
                
                if 'city' in filters:
                    param_count += 1
                    conditions.append(f"city = ${param_count}")
                    params.append(filters['city'])
                
                # Build query
                base_query = """
                    SELECT token, price, city, vehicle_data, first_seen, last_seen, is_sent
                    FROM vehicles
                """
                
                if conditions:
                    query = base_query + " WHERE " + " AND ".join(conditions)
                else:
                    query = base_query
                
                query += f" ORDER BY first_seen DESC LIMIT ${param_count + 1}"
                params.append(limit)
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                # Flatten results
                flattened_results = []
                for row in results:
                    flattened = dict(row['vehicle_data'])
                    flattened.update({
                        'token': row['token'],
                        'first_seen': row['first_seen'],
                        'last_seen': row['last_seen'],
                        'is_sent': row['is_sent']
                    })
                    flattened_results.append(flattened)
                
                return flattened_results

    def vehicle_exists(self, token: str) -> bool:
        """Check if a vehicle exists in the database by token"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM vehicles WHERE token = %s",
                    (token,)
                )
                return cur.fetchone() is not None

    def get_vehicle_by_token(self, token: str) -> Optional[Dict]:
        """Get vehicle data by token"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT token, price, city, vehicle_data, first_seen, last_seen, is_sent
                    FROM vehicles WHERE token = %s
                """, (token,))
                result = cur.fetchone()
                
                if result:
                    # Flatten the result for backward compatibility
                    flattened = dict(result['vehicle_data'])
                    flattened.update({
                        'token': result['token'],
                        'first_seen': result['first_seen'],
                        'last_seen': result['last_seen'],
                        'is_sent': result['is_sent']
                    })
                    return flattened
                return None
