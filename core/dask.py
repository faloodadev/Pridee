from distributed import Client
from typing import Optional
from utils.logger import log
import config

class DaskManager:
    def __init__(self):
        self.client: Optional[Client] = None

    async def setup(self) -> None:
        """Create and configure Dask client with dashboard."""
        try:
            self.client = await Client(
                asynchronous=True,
                dashboard_address=f"{config.DASK.HOST}:{config.DASK.PORT}",
                security=None if config.DASK.ALLOW_ANONYMOUS else {
                    'username': config.DASK.USERNAME,
                    'password': config.DASK.PASSWORD
                }
            )
            
            dashboard_link = self.client.dashboard_link
            log.info(f"Dask dashboard available at: {dashboard_link}")
            
        except Exception as e:
            log.exception(f"Failed to create Dask client: {e}")
            raise

    async def cleanup(self) -> None:
        """Cleanup Dask client"""
        if self.client:
            await self.client.close()
            self.client = None 