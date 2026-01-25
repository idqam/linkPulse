from datetime import datetime, timezone
import json
import logging

from pydantic import BaseModel

from app.core.redis import RedisSingleton
from app.events.constants import STREAM_NAME


logger = logging.getLogger(__name__)


class EventPublisher:
    def __init__(self):
        self._redis = None

    @property
    def redis(self):
        if self._redis is None:
            self._redis = RedisSingleton.get_instance()
        return self._redis

    async def publish(self, event_type: str, payload: BaseModel) -> str:
        try:
            event_data = {
                "type": event_type,
                "payload": payload.model_dump_json(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            message_id = await self.redis.xadd(STREAM_NAME, event_data)
            logger.debug(f"Published event {event_type} with id {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return ""

    async def publish_raw(self, event_type: str, payload: dict) -> str:
        try:
            event_data = {
                "type": event_type,
                "payload": json.dumps(payload),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            message_id = await self.redis.xadd(STREAM_NAME, event_data)
            logger.debug(f"Published event {event_type} with id {message_id}")
            return message_id
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")
            return ""


event_publisher = EventPublisher()
