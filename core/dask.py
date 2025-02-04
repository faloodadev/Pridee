from distributed import Client
from typing import Optional
from utils.logger import log
import config

async def create_dask_client() -> Client:
    """Create and configure Dask client with dashboard."""
    try:
        client = await Client(
            asynchronous=True,
            dashboard_address=f"{config.DASK.HOST}:{config.DASK.PORT}",
            security=None if config.DASK.ALLOW_ANONYMOUS else {
                'username': config.DASK.USERNAME,
                'password': config.DASK.PASSWORD
            }
        )
        
        dashboard_link = client.dashboard_link
        log.info(f"Dask dashboard available at: {dashboard_link}")
        
        return client
    except Exception as e:
        log.exception(f"Failed to create Dask client: {e}")
        raise 