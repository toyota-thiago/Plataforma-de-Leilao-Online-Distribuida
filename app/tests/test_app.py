import json
import os
import sys
import threading
import time
from datetime import datetime, timedelta

import fakeredis
import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import app as auction_app


@pytest.fixture(autouse=True)
def setup_fake_redis(monkeypatch):
    """Use fakeredis for all tests."""
    fake = fakeredis.FakeStrictRedis(decode_responses=True)
    # replace redis clients used by the app
    monkeypatch.setattr(auction_app, "r", fake)
    monkeypatch.setattr(auction_app, "pub", fake)
    # clear between tests
    fake.flushall()
    yield
    fake.flushall()


@pytest.fixture
def client():
    auction_app.app.config["TESTING"] = True
    return auction_app.app.test_client()


def future_time(hours=1):
    return (datetime.now() + timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")


def test_create_auction_success(client):
    payload = {
        "title": "Item A",
        "description": "Desc",
        "initial_price": 10,
        "end_time": future_time(),
    }
    resp = client.post("/create-auction", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["success"] is True
    auction_id = data["auction_id"]
    stored = auction_app.AuctionStorage.get_auction(auction_id)
    assert stored["title"] == "Item A"
    assert stored["active"] is True


def test_create_auction_missing_field(client):
    resp = client.post("/create-auction", json={"title": "X"})
    assert resp.status_code == 400
    assert "Missing field" in resp.get_json()["error"]


def test_create_auction_past_end_time(client):
    payload = {
        "title": "Item",
        "description": "Desc",
        "initial_price": 5,
        "end_time": (datetime.now() - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S"),
    }
    resp = client.post("/create-auction", json=payload)
    assert resp.status_code == 400
    assert "future" in resp.get_json()["error"]


def test_api_auctions_lists_created(client):
    client.post(
        "/create-auction",
        json={
            "title": "Item",
            "description": "Desc",
            "initial_price": 1,
            "end_time": future_time(),
        },
    )
    resp = client.get("/api/auctions")
    assert resp.status_code == 200
    auctions = resp.get_json()["auctions"]
    assert len(auctions) == 1
    assert auctions[0]["title"] == "Item"


def create_sample_auction(client, price=10):
    resp = client.post(
        "/create-auction",
        json={
            "title": "Sample",
            "description": "Desc",
            "initial_price": price,
            "end_time": future_time(),
        },
    )
    return resp.get_json()["auction_id"]


def test_place_bid_success(client):
    auction_id = create_sample_auction(client, price=10)
    resp = client.post(
        "/place-bid",
        json={"auction_id": auction_id, "amount": 20, "email": "a@a.com", "bidder": "Alice"},
    )
    assert resp.status_code == 200
    bids = auction_app.AuctionStorage.get_bids(auction_id)
    assert len(bids) == 1
    assert bids[0]["amount"] == 20
    assert bids[0]["bidder"] == "Alice"


def test_place_bid_lower_amount(client):
    auction_id = create_sample_auction(client, price=10)
    client.post(
        "/place-bid",
        json={"auction_id": auction_id, "amount": 20, "email": "a@a.com"},
    )
    resp = client.post(
        "/place-bid",
        json={"auction_id": auction_id, "amount": 15, "email": "b@b.com"},
    )
    assert resp.status_code == 400
    assert "higher" in resp.get_json()["error"]


def test_place_bid_missing_fields(client):
    auction_id = create_sample_auction(client, price=5)
    resp = client.post("/place-bid", json={"auction_id": auction_id})
    assert resp.status_code == 400
    assert "Missing field" in resp.get_json()["error"]


def test_place_bid_not_found(client):
    resp = client.post(
        "/place-bid", json={"auction_id": "nope", "amount": 10, "email": "a@a.com"}
    )
    assert resp.status_code == 404


def test_place_bid_expired(client, monkeypatch):
    auction_id = create_sample_auction(client, price=5)

    auction = auction_app.AuctionStorage.get_auction(auction_id)
    auction["end_time"] = (datetime.now() - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    auction_app.r.set(f"auction:{auction_id}", json.dumps(auction))

    resp = client.post(
        "/place-bid",
        json={"auction_id": auction_id, "amount": 10, "email": "a@a.com"},
    )
    assert resp.status_code == 400
    assert "expired" in resp.get_json()["error"]


def test_api_auction_details_returns_bids(client):
    auction_id = create_sample_auction(client, price=10)
    client.post(
        "/place-bid",
        json={"auction_id": auction_id, "amount": 20, "email": "a@a.com", "bidder": "Alice"},
    )
    resp = client.get(f"/api/auction/{auction_id}")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["auction"]["id"] == auction_id
    assert len(body["bids"]) == 1
    assert body["bids"][0]["amount"] == 20

