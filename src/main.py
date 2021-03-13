from os import stat
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRouter
import pydantic
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import mode
import uvicorn
from sqlalchemy.orm.session import sessionmaker
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from . import models
from . import schemas
from .database import LocalSession, engine
from .utils import time_to_hours, hours_to_time, type_to_weight, weight_to_type

models.Base.metadata.create_all(bind=engine)

router = APIRouter()

app = FastAPI()


def get_db():
    db = LocalSession()

    try:
        yield db
    finally:
        db.close()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
    body = exc.body  # https://github.com/tiangolo/fastapi/issues/1909

    if "/couriers" in request.url.path and request.method == "POST":
        broken_dolls = []

        for p_courier in body["data"]:
            try:
                schemas.CourierItem(**p_courier)
            except pydantic.ValidationError:
                broken_dolls.append(p_courier["courier_id"])

        return JSONResponse(content={"validation_error": {"couriers": [{"id": x} for x in broken_dolls]}}, status_code=400)

    elif "/orders" in request.url.path and request.method == "POST":
        broken_orders = []

        for rd in body["data"]:
            try:
                schemas.OrderItem(**rd)
            except pydantic.ValidationError:
                broken_orders.append(rd["order_id"])

        return JSONResponse(content={"validation_error": {"orders": [{"id": x} for x in broken_orders]}}, status_code=400)
    else:
        return Response(status_code=400)


@app.post("/couriers", status_code=201)
async def couriers_post(data: schemas.CouriersPostRequest, session: Session = Depends(get_db)):
    for cr in data.data:
        new_courier = models.Courier(
            id=cr.courier_id,
            max_w=type_to_weight(cr.courier_type),
            regions=[models.Region(region=x) for x in cr.regions],
            hours=[models.WorkHours(hours=x) for x in hours_to_time(cr.working_hours)])

        session.add(new_courier)

    session.commit()

    return {"couriers": [{"id": a.courier_id} for a in data.data]}


@app.patch("/couriers/{courier_id}")
async def couriers_patch(data: schemas.PatchCourierItem, courier_id: int, session: Session = Depends(get_db)):
    # TODO Check if some orders are vacant

    courier: models.Courier = session.query(models.Courier).filter(
        models.Courier.id == courier_id).first()

    if data.working_hours:
        courier.hours = [models.WorkHours(
            hours=x) for x in hours_to_time(data.working_hours)]
    if data.courier_type:
        courier.max_w = type_to_weight(data.courier_type)
    if data.regions:
        courier.regions = [models.Region(region=x) for x in data.regions]

    session.merge(courier)
    session.commit()

    return {
        "courier_id": courier_id,
        "courier_type": weight_to_type(courier.max_w),
        "regions": [r.region for r in courier.regions],
        "working_hours": time_to_hours(courier.hours)
    }



@app.get("/couriers/{courier_id}")
async def couriers_get(courier_id: int, session: Session = Depends(get_db)):
    courier: models.Courier = session.query(models.Courier).filter(
        models.Courier.id == courier_id).first()

    if not courier:
        raise HTTPException(status_code=400)

    return {
        "courier_id": courier_id,
        "courier_type": weight_to_type(courier.max_w),
        "regions": [r.region for r in courier.regions],
        "working_hours": time_to_hours(courier.hours)
    }


@app.post("/orders", status_code=201)
async def orders_post(data: schemas.OrdersPostRequest, session: Session = Depends(get_db)):
    for rd in data.data:
        order = models.Order(id=rd.order_id,
                             weight=rd.weight,
                             region=rd.region,
                             hours=[models.DeliveryHours(hours=x) for x in hours_to_time(rd.delivery_hours)])
        session.add(order)

    session.commit()

    return {"orders": [{"id": a.order_id} for a in data.data]}


@app.post("/orders/assign")
async def assign(data: schemas.AssignPostRequest, session: Session = Depends(get_db)):
    courier: models.Courier = session.query(models.Courier).filter(
        models.Courier.id == data.courier_id).first()

    if not courier:
        raise HTTPException(status_code=400)

    possible_orders = session.query(models.Order).filter(models.Order.taken == None).filter(
        models.Order.weight <= courier.max_w).filter(models.Order.region.in_([x.region for x in courier.regions])).all()

    print(possible_orders)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)