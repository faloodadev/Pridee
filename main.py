import asyncio
import logging
from dask.distributed import Client as DaskClient
import config

from core.bot import Evict
from utils.optimization import setup_cpu_optimizations
from utils.monitoring import setup_monitoring
from utils.logger import setup_logging
from utils.monitoring import cleanup_monitoring

log = logging.getLogger(__name__)

def calculate_shard_ids(cluster_id: int, cluster_count: int, total_shards: int) -> list[int]:
    """Calculate shard IDs for a given cluster."""
    shards_per_cluster = total_shards // cluster_count
    start_shard = cluster_id * shards_per_cluster
    end_shard = start_shard + shards_per_cluster
    return list(range(start_shard, end_shard))

async def start_cluster(shard_ids, shard_count, **kwargs):
    """Start a cluster of shards."""
    bot = Evict(
        shard_ids=shard_ids,
        shard_count=shard_count,
        description=config.CLIENT.DESCRIPTION,
        owner_ids=config.CLIENT.OWNER_IDS,
        **kwargs
    )
    try:
        await bot.start(config.TOKEN)
    except Exception as e:
        log.error(f"Failed to start cluster with shards {shard_ids}: {e}")
        raise

async def main():
    try:
        
        setup_logging()

        dask_client = await DaskClient(asynchronous=True)
        
        cluster_tasks = []
        for i in range(config.SHARDING.CLUSTER_COUNT):
            shard_ids = calculate_shard_ids(i, config.SHARDING.CLUSTER_COUNT, config.SHARDING.TOTAL_SHARDS)
            cluster_tasks.append(
                start_cluster(
                    shard_ids=shard_ids,
                    shard_count=config.SHARDING.TOTAL_SHARDS,
                    dask_client=dask_client
                )
            )
        
        await asyncio.gather(*cluster_tasks)
        
    except Exception as e:
        log.exception(f"Fatal error in main: {e}")
        raise
    finally:
        await dask_client.close()
        await cleanup_monitoring()
        setup_logging.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        raise
