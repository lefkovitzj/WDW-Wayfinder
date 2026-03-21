from typing import List, Optional
from sqlalchemy import Column, TEXT
from sqlmodel import SQLModel, Field, ARRAY

class TransitAnalytics(SQLModel, table=True):
    __tablename__ = "transit_analytics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    origin_id: str
    destination_id: str
    # This uses the native Postgres ARRAY type for intermediate stops
    intermediate_stops: List[str] = Field(sa_column=Column(ARRAY(TEXT)))
    total_steps: int