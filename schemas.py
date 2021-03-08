from pydantic import BaseModel
from typing import List, Optional

class CourierItem(BaseModel):
     courier_id: int
     courier_type: str
     regions: List[int]
     working_hours: List[str]

class PatchCourierItem(BaseModel):
     courier_id: int
     courier_type: Optional[List[int]]
     regions: Optional[List[int]]
     working_hours: Optional[List[str]]

class CouriersPostRequest(BaseModel):
    data: List[CourierItem]

