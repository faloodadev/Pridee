from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime, timedelta
from utils.logger import log
from opentelemetry import trace
from redis.asyncio import Redis
import config

class ClusterIPC:
    def __init__(self, bot, cluster_id: int):
        self.bot = bot
        self.cluster_id = cluster_id
        self.redis: Optional[Redis] = None
        self.pubsub = None
        self.handlers: Dict[str, Callable] = {}
        self.listener_task = None
        self.heartbeat_task = None
        self._stop_event = asyncio.Event()
        self.last_heartbeat = 0
        self.tracer = trace.get_tracer(__name__)
        log.info(f"IPC initialized for cluster {cluster_id}")

    async def start(self):
        """Start the IPC system."""
        try:
            self.redis = Redis.from_url(config.REDIS.DSN)
            self.pubsub = self.redis.pubsub()
            log.info("Created Redis pubsub")
            
            await self.pubsub.subscribe(f"cluster_{self.cluster_id}")
            log.info(f"Subscribed to cluster_{self.cluster_id}")
            
            self.listener_task = asyncio.create_task(
                self._listen(), 
                name=f"ipc_listener_{self.cluster_id}"
            )
            log.info("Created listener task")
            
            await self.send_heartbeat()
            log.info("Sent initial heartbeat")
            
            self.heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(),
                name=f"ipc_heartbeat_{self.cluster_id}"
            )
            log.info("Started heartbeat task")
            
            log.info("IPC fully initialized")
            
        except Exception as e:
            log.error(f"Failed to start IPC: {e}", exc_info=True)
            raise

    async def _listen(self):
        """Listen for messages."""
        try:
            while not self._stop_event.is_set():
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message is None:
                    await asyncio.sleep(0.1)
                    continue
                    
                try:
                    data = json.loads(message['data'])
                    if handler := self.handlers.get(data['action']):
                        await handler(data['data'])
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    log.error(f"Error handling IPC message: {e}", exc_info=True)
                    
        except asyncio.CancelledError:
            log.info("IPC listener cancelled")
        except Exception as e:
            log.error(f"IPC listener error: {e}", exc_info=True)
        finally:
            await self.cleanup()

    async def _heartbeat_loop(self):
        """Send periodic heartbeats."""
        try:
            while not self._stop_event.is_set():
                await self.send_heartbeat()
                await asyncio.sleep(30)  
        except asyncio.CancelledError:
            log.info("Heartbeat loop cancelled")
        except Exception as e:
            log.error(f"Heartbeat loop error: {e}", exc_info=True)

    async def send_heartbeat(self):
        """Send a heartbeat message."""
        try:
            await self.redis.publish(
                "cluster_heartbeat",
                json.dumps({
                    "cluster_id": self.cluster_id,
                    "shard_count": len(self.bot.shards),
                    "guilds": len(self.bot.guilds),
                    "users": len(self.bot.users),
                    "timestamp": asyncio.get_event_loop().time()
                })
            )
            self.last_heartbeat = asyncio.get_event_loop().time()
            log.debug(f"Sent heartbeat for cluster {self.cluster_id}")
        except Exception as e:
            log.error(f"Failed to send heartbeat: {e}", exc_info=True)

    def add_handler(self, action: str, handler: Callable):
        """Add a message handler."""
        self.handlers[action] = handler
        log.info(f"Added handler for {action}")

    async def cleanup(self):
        """Cleanup IPC resources."""
        self._stop_event.set()
        
        if self.listener_task:
            self.listener_task.cancel()
            
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()
            
        if self.redis:
            await self.redis.close()
            
        log.info("IPC cleanup complete")

    async def broadcast(self, command: str, data: Optional[Dict[str, Any]] = None):
        """Broadcast message to all clusters."""
        with self.tracer.start_as_current_span("ipc_broadcast") as span:
            span.set_attribute("ipc.command", command)
            message = json.dumps({
                "command": command,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat(),
                "source_cluster": self.cluster_id
            })
            
            for cluster_id in range(self.bot.cluster_count):
                await self.redis.publish(f"cluster_{cluster_id}", message)

    async def send_to_cluster(self, cluster_id: int, command: str, data: Optional[Dict[str, Any]] = None):
        """Send message to specific cluster."""
        with self.tracer.start_as_current_span("ipc_send") as span:
            span.set_attribute("ipc.command", command)
            span.set_attribute("ipc.target_cluster", cluster_id)
            
            message = json.dumps({
                "command": command,
                "data": data or {},
                "timestamp": datetime.utcnow().isoformat(),
                "source_cluster": self.cluster_id
            })
            
            await self.redis.publish(f"cluster_{cluster_id}", message)

    async def get_cluster_status(self) -> List[Dict[str, Any]]:
        """Get status of all clusters."""
        with self.tracer.start_as_current_span("ipc_status"):
            status = []
            for cluster_id in range(self.bot.cluster_count):
                last_heartbeat = await self.redis.get(f"cluster_{cluster_id}_heartbeat")
                if last_heartbeat:
                    last_heartbeat = datetime.fromisoformat(last_heartbeat)
                    is_alive = datetime.utcnow() - last_heartbeat < timedelta(seconds=30)
                else:
                    is_alive = False
                    
                status.append({
                    "cluster_id": cluster_id,
                    "alive": is_alive,
                    "last_heartbeat": last_heartbeat.isoformat() if last_heartbeat else None
                })
            return status 