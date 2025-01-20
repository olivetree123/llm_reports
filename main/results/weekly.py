from typing import Optional

from pydantic import BaseModel


class WeeklyStats(BaseModel):
    env: Optional[str] = ""
    week_start_date: str
    week_end_date: str
    counts: dict
    rates: dict
    labels: dict

    class Config:
        from_attributes = True
