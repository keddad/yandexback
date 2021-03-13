from .database import Base
from pydantic import BaseModel, Extra
from typing import List, Optional


class ForbidAdditioalBase(BaseModel):
    class Config:
        extra = Extra.forbid


class CourierItem(ForbidAdditioalBase):
    courier_id: int
    courier_type: str
    regions: List[int]
    working_hours: List[str]


class OrderItem(ForbidAdditioalBase):
    order_id: int
    weight: float
    region: int
    delivery_hours: List[str]


class OrdersPostRequest(ForbidAdditioalBase):
    data: List[OrderItem]


class PatchCourierItem(ForbidAdditioalBase):
    courier_type: Optional[str]
    regions: Optional[List[int]]
    working_hours: Optional[List[str]]
    


class CouriersPostRequest(ForbidAdditioalBase):
    data: List[CourierItem]


class AssignPostRequest(ForbidAdditioalBase):
    courier_id: int
