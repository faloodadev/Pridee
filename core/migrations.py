"""Database migrations for missing tables."""
import asyncpg
from utils.logger import log


async def run_migrations(pool: asyncpg.Pool) -> None:
    """Run database migrations using the existing connection pool.
    
    Args:
        pool: The existing asyncpg connection pool from the bot
    """
    try:
        log.info("Running database migrations...")
        
        async with pool.acquire() as conn:
            log.info("Creating timer schema...")
            await conn.execute("CREATE SCHEMA IF NOT EXISTS timer;")
            
            log.info("Creating counter table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS public.counter (
                    guild_id bigint NOT NULL,
                    channel_id bigint NOT NULL,
                    option text NOT NULL,
                    last_update timestamp with time zone DEFAULT now() NOT NULL,
                    rate_limited_until timestamp with time zone
                );
            """)
            
            log.info("Creating timer.message table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS timer.message (
                    guild_id bigint NOT NULL,
                    channel_id bigint NOT NULL,
                    template text NOT NULL,
                    "interval" integer NOT NULL,
                    next_trigger timestamp with time zone NOT NULL
                );
            """)
            
            log.info("Creating timer.purge table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS timer.purge (
                    guild_id bigint NOT NULL,
                    channel_id bigint NOT NULL,
                    "interval" integer NOT NULL,
                    next_trigger timestamp with time zone NOT NULL,
                    method text DEFAULT 'bulk'::text NOT NULL
                );
            """)
            
        log.info("Database migrations completed successfully")
        
    except Exception as e:
        log.error(f"Failed to run migrations: {e}", exc_info=True)
        # Don't raise - let the bot continue even if migrations fail
