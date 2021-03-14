from .main import get_db, app
from .database import Base

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


TEST_DB = "sqlite://"
EXAMPLE_COURIERS = [({"data": [{"courier_id": 1, "courier_type": "foot", "regions": [1, 2, 32], "working_hours": ["09:00-18:00"]}]},
                     {"couriers": [{"id": 1}]}),
                    ({"data": [{"courier_id": 2, "courier_type": "bike", "regions": [1, 3, 12], "working_hours": ["09:00-18:00", "04:00-08:00"]}, {"courier_id": 3, "courier_type": "bike", "regions": [1, 2, 4, 5, 7, 12], "working_hours": ["09:00-18:00", "04:00-08:00"]}]},
                     {"couriers": [{"id": 2}, {"id": 3}]}),
                    ({"data": [{"courier_id": 4, "courier_type": "car", "regions": [1, 2, 3, 4, 5, 6, 32], "working_hours": ["09:00-18:00"]}]},
                     {"couriers": [{"id": 4}]})]

EXAMPLE_ORDERS = [({"data": [{"order_id": 1, "weight": 0.23, "region": 12, "delivery_hours": ["09:00-18:00"]}]},
                   {"orders": [{"id": 1}]}),
                  ({"data": [{"order_id": 2, "weight": 2.3, "region": 1, "delivery_hours": ["09:00-18:00"]}, {"order_id": 3, "weight": 23, "region": 3, "delivery_hours": ["04:00-05:00"]}]},
                   {"orders": [{"id": 2}, {"id": 3}]}),
                  ({"data": [{"order_id": 4, "weight": 43, "region": 2, "delivery_hours": ["09:00-18:00"]}]},
                   {"orders": [{"id": 4}]})]


def get_db_override():
    engine = create_engine(
        TEST_DB, connect_args={"check_same_thread": False}
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    return override_get_db


@pytest.fixture
def client():
    app.dependency_overrides[get_db] = get_db_override()
    client = TestClient(app)
    return client


@pytest.fixture
def filled_client(client):
    for c in EXAMPLE_COURIERS:
        client.post(
            "/couriers",
            json=c[0]
        )

    for c in EXAMPLE_ORDERS:
        client.post(
            "/orders",
            json=c[0]
        )

    return client


@pytest.fixture
def filled_client_assigned(filled_client):
    for data in EXAMPLE_COURIERS:
        for c in data[0]["data"]:
            filled_client.post(
                "/orders/assign",
                json={"courier_id": c["courier_id"]}
            )

    return filled_client


class TestCourierPost:
    @pytest.mark.parametrize("payload,exp_res",
                             EXAMPLE_COURIERS)
    def test_post(self, client, payload, exp_res):
        response = client.post(
            "/couriers",
            json=payload
        )

        assert response.status_code == 201
        assert response.json() == exp_res

    def test_invalid_data(self, client):
        response = client.post(
            "/couriers",
            json={
                "data": [{"courier_id": 1, "courier_type": "foot", "regions": [1, 2, 32]}]}
        )

        assert response.status_code == 400
        assert response.json() == {"validation_error": {
            "couriers": [{"id": 1}]}}


class TestOrderPost:
    @pytest.mark.parametrize("payload,exp_res",
                             EXAMPLE_ORDERS)
    def test_post(self, client, payload, exp_res):
        response = client.post(
            "/orders",
            json=payload
        )

        assert response.status_code == 201
        assert response.json() == exp_res

    def test_invalid_data(self, client):
        response = client.post(
            "/orders",
            json={
                "data": [{"order_id": 1, "weight": 0.23, "region": 12}]}
        )

        assert response.status_code == 400
        assert response.json() == {"validation_error": {
            "orders": [{"id": 1}]}}


class TestCourierPatch:
    def test_patch(self, filled_client):
        response = filled_client.patch(
            "/couriers/1",
            json={"courier_type": "bike", "regions": [1, 2]}
        )

        assert response.json() == {"courier_type": "bike", "regions": [
            1, 2], "courier_id": 1, "working_hours": ["09:00-18:00"]}

    def test_invalid_data(self, filled_client):
        response = filled_client.patch(
            "/couriers/1",
            json={"roses": "red"}
        )

        assert response.status_code == 400

    @pytest.mark.parametrize("change", [{"regions": [69]}, {"working_hours": ["00:00-00:10"]}, {"courier_type": "foot"}])
    def test_remove_oders(self, filled_client_assigned, change):
        filled_client_assigned.patch(
            "/couriers/4",
            json=change
        )

        o_4 = filled_client_assigned.get("/orders/4").json()

        assert o_4["taken"] == None
        assert o_4["courier_id"] == None


class TestOrdersAssign:
    @pytest.mark.parametrize("c_id,exp_res", [(1, [{"id": 2}]), (2, [{"id": 1}, {"id": 2}]), (4, [{"id": 2}, {"id": 4}])])
    def test_assign(self, filled_client, c_id, exp_res):
        response = filled_client.post(
            "/orders/assign",
            json={"courier_id": c_id}
        )

        assert response.status_code == 200
        assert response.json()["orders"] == exp_res

class TestOrdersComplete:
    def test_complete(self, filled_client_assigned):
        response = filled_client_assigned.post(
            "/orders/complete",
            json={"courier_id": 4, "order_id": 4, "complete_time": "2021-01-10T10:33:01.42Z"}
        )

        assert response.json()["order_id"] == 4

        order = filled_client_assigned.get("/orders/4").json()

        assert "2021-01-10T10:33:01.42" in order["done"]