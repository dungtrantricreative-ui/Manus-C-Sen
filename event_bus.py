from typing import Callable, Awaitable, List
import asyncio

class EventBus:
    _instance = None
    _listeners: List[Callable[[dict], Awaitable[None]]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._listeners = []
        return cls._instance

    @classmethod
    def subscribe(cls, listener: Callable[[dict], Awaitable[None]]):
        cls._listeners.append(listener)

    @classmethod
    async def publish(cls, event_type: str, content: str = None, **kwargs):
        """
        Publish an event to all subscribers.
        common types: 'status' (thinking), 'terminal' (commands), 'browser' (screenshots)
        """
        payload = {
            "type": event_type,
            "content": content,
            **kwargs
        }
        for listener in cls._listeners:
            try:
                await listener(payload)
            except Exception as e:
                print(f"Error in event listener: {e}")

# Global instance
bus = EventBus()
