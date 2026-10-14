from typing import Optional

from pydantic import BaseModel


class QueueSnapshot(BaseModel):
    doctor_id: int
    current_token_number: Optional[int]
    waiting_count: int
    own_token_number: Optional[int]
    position: Optional[int]
    estimated_wait_minutes: Optional[int]