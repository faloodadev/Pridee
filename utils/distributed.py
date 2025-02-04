from dask.distributed import Client as DaskClient
from multiprocessing import Pool, cpu_count
from typing import Optional
import logging

log = logging.getLogger(__name__)

class DistributedProcessing:
    def __init__(self):
        self.dask_client: Optional[DaskClient] = None
        self.process_pool: Optional[Pool] = None
        self.logical_cpu_count = cpu_count()

    async def setup(self):
        """Initialize distributed processing"""
        try:
            self.dask_client = await DaskClient(asynchronous=True)
            
            self.process_pool = Pool(
                processes=min(4, self.logical_cpu_count),
                maxtasksperchild=100
            )
            log.info("Distributed processing initialized")
        except Exception as e:
            log.error(f"Failed to initialize distributed processing: {e}")
            raise

    async def cleanup(self):
        """Cleanup distributed processing resources"""
        if self.dask_client:
            await self.dask_client.close()
        
        if self.process_pool:
            self.process_pool.close()
            self.process_pool.join()

    async def submit_task(self, func, *args, **kwargs):
        """Submit a task to Dask"""
        if not self.dask_client:
            raise RuntimeError("Dask client not initialized")
        return await self.dask_client.submit(func, *args, **kwargs)

    def submit_pool_task(self, func, *args, **kwargs):
        """Submit a task to process pool"""
        if not self.process_pool:
            raise RuntimeError("Process pool not initialized")
        return self.process_pool.apply_async(func, args=args, kwds=kwargs) 