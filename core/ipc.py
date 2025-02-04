from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, Optional, List, Callable
from datetime import datetime, timedelta
from utils.logger import log
from opentelemetry import trace

class ClusterIPC:
    def __init__(self, bot, cluster_id: int):
        self.bot = bot
        self.cluster_id = cluster_id
        self.redis = bot.redis
        self.tracer = trace.get_tracer(__name__)
        self.handlers: Dict[str, Callable] = {}
        self.subscribed = False
        
    async def start(self):
        """Start IPC listener."""
        with self.tracer.start_as_current_span("ipc_start"):
            self.pubsub = self.redis.pubsub()
            await self.pubsub.subscribe(f"cluster_{self.cluster_id}")
            self.subscribed = True
            self.bot.loop.create_task(self._listener())
            log.info(f"IPC started for cluster {self.cluster_id}")

    async def stop(self):
        """Stop IPC listener."""
        with self.tracer.start_as_current_span("ipc_stop"):
            if self.subscribed:
                await self.pubsub.unsubscribe()
                self.subscribed = False
                log.info(f"IPC stopped for cluster {self.cluster_id}")

    async def _listener(self):
        """Listen for IPC messages."""
        try:
            while self.subscribed:
                message = await self.pubsub.get_message(ignore_subscribe_messages=True)
                if message and message["type"] == "message":
                    with self.tracer.start_as_current_span("ipc_message") as span:
                        try:
                            data = json.loads(message["data"])
                            span.set_attribute("ipc.command", data.get("command"))
                            
                            if handler := self.handlers.get(data["command"]):
                                await handler(data.get("data", {}))
                            
                        except Exception as e:
                            log.error(f"Error processing IPC message: {e}")
                            span.record_exception(e)
                await asyncio.sleep(0.1)
                
        except Exception as e:
            log.error(f"IPC listener error: {e}")
            if self.subscribed:
                self.bot.loop.create_task(self._listener())

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

    def add_handler(self, command: str, handler: Callable):
        """Add command handler."""
        self.handlers[command] = handler

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

    async def heartbeat(self):
        """Send cluster heartbeat."""
        await self.redis.set(
            f"cluster_{self.cluster_id}_heartbeat",
            datetime.utcnow().isoformat(),
            ex=60
        ) 