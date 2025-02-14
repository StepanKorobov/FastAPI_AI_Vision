from typing import List

from pydantic import BaseModel


class Camera(BaseModel):
    message: str


class Humans(BaseModel):
    images: List[str]
