from typing import Optional

from pydantic import BaseModel


class DailyStats(BaseModel):
    env: Optional[str] = ""
    date: str
    counts: dict
    rates: dict
    labels: dict

    class Config:
        from_attributes = True
