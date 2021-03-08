from pydantic import BaseModel
from typing import List, Optional

class CourierItem(BaseModel):
     courier_id: int
     courier_type: str
     regions: List[int]
     working_hours: List[str]

class OrderItem(BaseModel):
     order_id: int
     weight: float
     region: int
     delivery_hours: List[str]

class OrdersPostRequest(BaseModel):
     data: List[OrderItem]

class PatchCourierItem(BaseModel):
     courier_type: Optional[str]
     regions: Optional[List[int]]
     working_hours: Optional[List[str]]

class CouriersPostRequest(BaseModel):
    data: List[CourierItem]

