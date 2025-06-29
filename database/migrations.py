#!/usr/bin/env python3
"""
Database migrations for Yad2 Telegram Bot
Simple migration system to handle schema changes
"""

import os
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, database_url=None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url)
    
    def create_migrations_table(self):
        """Create migrations tracking table"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version VARCHAR(255) PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                conn.commit()
    
    def is_migration_applied(self, version):
        """Check if a migration has been applied"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM schema_migrations WHERE version = %s",
                    (version,)
                )
                return cur.fetchone() is not None
    
    def mark_migration_applied(self, version):
        """Mark a migration as applied"""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,)
                )
                conn.commit()
    
    def run_migration(self, version, description, sql):
        """Run a single migration"""
        if self.is_migration_applied(version):
            logger.info(f"Migration {version} already applied, skipping")
            return
        
        logger.info(f"Running migration {version}: {description}")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                # Execute migration SQL
                cur.execute(sql)
                
                # Mark as applied
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,)
                )
                
                conn.commit()
                logger.info(f"Migration {version} completed successfully")
    
    def run_all_migrations(self):
        """Run all pending migrations"""
        self.create_migrations_table()
        
        # Define migrations here
        migrations = [
            {
                'version': '001_initial_schema',
                'description': 'Create initial vehicles table with JSONB',
                'sql': """
                    CREATE TABLE IF NOT EXISTS vehicles (
                        ad_number BIGINT PRIMARY KEY,
                        manufacturer_id INTEGER NOT NULL,
                        model_id INTEGER NOT NULL,
                        price INTEGER,
                        city TEXT,
                        vehicle_data JSONB NOT NULL,
                        first_seen TIMESTAMP DEFAULT NOW(),
                        last_seen TIMESTAMP DEFAULT NOW(),
                        is_sent BOOLEAN DEFAULT FALSE
                    );
                    
                    -- Essential indexes for performance
                    CREATE INDEX IF NOT EXISTS idx_vehicles_ad_number 
                    ON vehicles (ad_number);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_manufacturer_model 
                    ON vehicles (manufacturer_id, model_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_first_seen 
                    ON vehicles (first_seen);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_is_sent 
                    ON vehicles (is_sent);
                    
                    -- JSONB indexes for common queries
                    CREATE INDEX IF NOT EXISTS idx_vehicles_price_range 
                    ON vehicles USING GIN ((vehicle_data->'price'));
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_production_year 
                    ON vehicles USING GIN ((vehicle_data->'productionDate'));
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_km 
                    ON vehicles USING GIN ((vehicle_data->'km'));
                    
                    -- General JSONB index for other queries
                    CREATE INDEX IF NOT EXISTS idx_vehicles_data 
                    ON vehicles USING GIN (vehicle_data);
                """
            },
            {
                'version': '002_change_primary_key_to_token',
                'description': 'Change primary key from ad_number to token',
                'sql': """
                    -- Create new table with token as primary key
                    CREATE TABLE IF NOT EXISTS vehicles_new (
                        token TEXT PRIMARY KEY,
                        manufacturer_id INTEGER NOT NULL,
                        model_id INTEGER NOT NULL,
                        price INTEGER,
                        city TEXT,
                        vehicle_data JSONB NOT NULL,
                        first_seen TIMESTAMP DEFAULT NOW(),
                        last_seen TIMESTAMP DEFAULT NOW(),
                        is_sent BOOLEAN DEFAULT FALSE
                    );
                    
                    -- Copy data from old table to new table, using token from vehicle_data
                    INSERT INTO vehicles_new (
                        token, manufacturer_id, model_id, price, city,
                        vehicle_data, first_seen, last_seen, is_sent
                    )
                    SELECT 
                        vehicle_data->>'token' as token,
                        manufacturer_id,
                        model_id,
                        price,
                        city,
                        vehicle_data,
                        first_seen,
                        last_seen,
                        is_sent
                    FROM vehicles
                    WHERE vehicle_data->>'token' IS NOT NULL
                    AND vehicle_data->>'token' != '';
                    
                    -- Drop old table and rename new table
                    DROP TABLE IF EXISTS vehicles;
                    ALTER TABLE vehicles_new RENAME TO vehicles;
                    
                    -- Recreate indexes for the new structure
                    CREATE INDEX IF NOT EXISTS idx_vehicles_token 
                    ON vehicles (token);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_manufacturer_model 
                    ON vehicles (manufacturer_id, model_id);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_first_seen 
                    ON vehicles (first_seen);
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_is_sent 
                    ON vehicles (is_sent);
                    
                    -- JSONB indexes for common queries
                    CREATE INDEX IF NOT EXISTS idx_vehicles_price_range 
                    ON vehicles USING GIN ((vehicle_data->'price'));
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_production_year 
                    ON vehicles USING GIN ((vehicle_data->'productionDate'));
                    
                    CREATE INDEX IF NOT EXISTS idx_vehicles_km 
                    ON vehicles USING GIN ((vehicle_data->'km'));
                    
                    -- General JSONB index for other queries
                    CREATE INDEX IF NOT EXISTS idx_vehicles_data 
                    ON vehicles USING GIN (vehicle_data);
                """
            },
            # Future migrations can be added here
            # {
            #     'version': '003_add_new_column',
            #     'description': 'Add new column for feature X',
            #     'sql': 'ALTER TABLE vehicles ADD COLUMN new_column TEXT;'
            # },
        ]
        
        for migration in migrations:
            self.run_migration(
                migration['version'],
                migration['description'],
                migration['sql']
            )
        
        logger.info("All migrations completed successfully")
    
    def get_migration_status(self):
        """Get status of all migrations"""
        self.create_migrations_table()
        
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT version, applied_at FROM schema_migrations ORDER BY applied_at"
                )
                return cur.fetchall()

def main():
    """Run migrations from command line"""
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    runner = MigrationRunner()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        print("Migration Status:")
        print("=" * 50)
        
        status = runner.get_migration_status()
        if status:
            for migration in status:
                print(f"✅ {migration['version']} - Applied at {migration['applied_at']}")
        else:
            print("No migrations have been applied yet")
    else:
        print("Running database migrations...")
        runner.run_all_migrations()
        print("✅ Migrations completed!")

if __name__ == "__main__":
    main() 