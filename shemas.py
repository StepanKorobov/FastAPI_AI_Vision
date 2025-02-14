from datetime import datetime

from pydantic import BaseModel, field_validator, Field


class Date(BaseModel):
    start_date: datetime = Field(default="2025-01-01 00:00:00")
    end_date: datetime = Field(default="2025-01-01 00:00:00")

    @field_validator('start_date', mode="before")
    def start_data_validator(cls, v):
        return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')

    @field_validator('end_date', mode="before")
    def end_data_validator(cls, v):
        return datetime.strptime(v, '%Y-%m-%d %H:%M:%S')
