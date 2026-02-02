from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class Event(BaseModel):
    id: str = Field(default_factory=lambda: datetime.now().strftime("%Y%m%d%H%M%S%f"))
    timestamp: datetime = Field(default_factory=datetime.now)
    type: str # 'action' or 'observation'
    name: str
    content: Any
    meta: Dict[str, Any] = Field(default_factory=dict)

class EventBus:
    """A central hub for agent events (OpenHands style)."""
    
    def __init__(self):
        self.events: List[Event] = []
        self._listeners = []

    def emit(self, event_type: str, name: str, content: Any, meta: Optional[Dict] = None):
        event = Event(type=event_type, name=name, content=content, meta=meta or {})
        self.events.append(event)
        for listener in self._listeners:
            listener(event)
        return event

    def get_actions(self) -> List[Event]:
        return [e for e in self.events if e.type == 'action']

    def get_observations(self) -> List[Event]:
        return [e for e in self.events if e.type == 'observation']

    def clear(self):
        self.events = []
