from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.orm import relationship

from database import Base


class Courier(Base):
    __tablename__ = "couriers"
    id = Column(Integer, primary_key=True)
    max_w = Column(Integer)

    regions = relationship("Region")
    hours = relationship("WorkHours")
    orders = relationship("Order")


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    weight = Column(Integer)
    region = Column(Integer)
    taken = Column(DateTime)
    done = Column(DateTime)
    courier_id = Column(Integer, ForeignKey("couriers.id"))
    hours = relationship("DeliveryHours")


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    region = Column(Integer)

    courier_id = Column(Integer, ForeignKey("couriers.id"))


class WorkHours(Base):
    __tablename__ = "workhours"
    id = Column(Integer, primary_key=True, autoincrement=True)

    courier_id = Column(Integer, ForeignKey("couriers.id"))
    hours = Column(DateTime)


class DeliveryHours(Base):
    __tablename__ = "delhours"
    id = Column(Integer, primary_key=True, autoincrement=True)

    courier_id = Column(Integer, ForeignKey("orders.id"))
    hours = Column(DateTime)
