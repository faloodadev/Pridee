#!/usr/bin/env python3
"""Create missing database tables for timer and statistics features."""
import asyncio
import asyncpg
from os import getenv
from dotenv import load_dotenv

load_dotenv()

async def create_tables():
    """Create the missing tables."""
    dsn = getenv("DATABASE_URL", "postgresql://postgres:admin@localhost/evict")
    
    print(f"Connecting to database...")
    try:
        # Use a single connection instead of a pool
        conn = await asyncpg.connect(dsn, timeout=10)
        
        print("Creating timer schema...")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS timer;")
        
        print("Creating counter table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS public.counter (
                guild_id bigint NOT NULL,
                channel_id bigint NOT NULL,
                option text NOT NULL,
                last_update timestamp with time zone DEFAULT now() NOT NULL,
                rate_limited_until timestamp with time zone
            );
        """)
        
        print("Creating timer.message table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS timer.message (
                guild_id bigint NOT NULL,
                channel_id bigint NOT NULL,
                template text NOT NULL,
                "interval" integer NOT NULL,
                next_trigger timestamp with time zone NOT NULL
            );
        """)
        
        print("Creating timer.purge table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS timer.purge (
                guild_id bigint NOT NULL,
                channel_id bigint NOT NULL,
                "interval" integer NOT NULL,
                next_trigger timestamp with time zone NOT NULL,
                method text DEFAULT 'bulk'::text NOT NULL
            );
        """)
        
        await conn.close()
        print("✓ All tables created successfully!")
        
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
