from datetime import datetime
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRouter
import pydantic
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, engine
import uvicorn
from sqlalchemy.orm.session import sessionmaker
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import dateutil.parser

from . import models
from . import schemas
from .utils import earnings, time_to_hours, hours_to_time, type_to_weight, weight_to_type, filter_time_orders, rating

app = FastAPI()


def get_db():
    DATABASE_URL = "postgresql+psycopg2://postgres:password@postgres:5432/"

    engine = create_engine(DATABASE_URL)
    LocalSession = sessionmaker(bind=engine)

    models.Base.metadata.create_all(bind=engine)

    db = LocalSession()

    try:
        yield db
    finally:
        db.close()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc):
    try:
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
    except:
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
    courier: models.Courier = session.query(models.Courier).filter(
        models.Courier.id == courier_id).first()

    if not courier:
        raise HTTPException(status_code=400)

    broken_orders = set()

    if data.working_hours:
        courier.hours = [models.WorkHours(
            hours=x) for x in hours_to_time(data.working_hours)]

        possible_orders = filter_time_orders(courier, courier.orders)

        for o in courier.orders:
            if o not in possible_orders and not o.done:
                broken_orders.add(o)

    if data.courier_type:
        courier.max_w = type_to_weight(data.courier_type)

        for o in courier.orders:
            if o.weight > courier.max_w and not o.done:
                broken_orders.add(o)

    if data.regions: 
        courier.regions = [models.Region(region=x) for x in data.regions]

        for o in courier.orders:
            if o.region not in [x.region for x in courier.regions] and not o.done:
                broken_orders.add(o)

    for el in broken_orders:
        el.courier_id = None
        el.taken = None

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

    if not courier or sum([bool(o.done) for o in courier.orders]) == 0:
        raise HTTPException(status_code=400)

    return {
        "courier_id": courier_id,
        "courier_type": weight_to_type(courier.max_w),
        "regions": [r.region for r in courier.regions],
        "working_hours": time_to_hours(courier.hours),
        "rating": rating(courier),
        "earnings": earnings(courier, session)
    }


@app.get("/orders/{order_id}")  # for testing
async def orders_get(order_id: int, session: Session = Depends(get_db)):
    order: models.Order = session.query(models.Order).filter(
        models.Order.id == order_id).first()

    return {
        "order_id": order.id,
        "weight": order.weight,
        "region": order.region,
        "taken": order.taken,
        "done": order.done,
        "courier_id": order.courier_id
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

    orders_to_take = filter_time_orders(courier, possible_orders)
    assign_time = datetime.now()

    for o in orders_to_take:
        o.taken = assign_time
        o.courier_id = data.courier_id

    session.commit()

    if orders_to_take:
        return {"orders": [{"id": a.id} for a in orders_to_take], "assign_time": assign_time}
    else:
        return {"orders": []}


@app.post("/orders/complete")
async def orders_complete(data: schemas.OrderCompletePost, session: Session = Depends(get_db)):
    order = session.query(models.Order).filter(
        models.Order.id == data.order_id).first()

    if not order or not order.taken or order.courier_id != data.courier_id:
        raise HTTPException(status_code=400)

    order.done = dateutil.parser.parse(data.complete_time)

    session.commit()

    return {"order_id": order.id}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
