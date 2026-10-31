"""Script for checkout service"""
import os
import redis
import requests

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()

redis_client = redis.Redis(
    host=os.getenv("HOST"),
    port=6379,
    db=0,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5
)

# Test Redis connection
try:
    redis_client.ping()
except redis.ConnectionError as e:
    print(f"Warning: Could not connect to Redis: {str(e)}")

INVENTORY_SERVICE_URL = "http://127.0.0.1:8001"
USERS_SERVICE_URL = "http://127.0.0.1:8002"


@app.post("/checkout/{user_id}/{book_id}")
def checkout_book(user_id: int, book_id: int):
    """Function to checkout book"""
    checkout_response = requests.put(
        f"{INVENTORY_SERVICE_URL}/books/{book_id}/checkout",
        params={"user_id": user_id}, timeout=10000)
    if checkout_response.status_code != 200:
        raise HTTPException(
            status_code=checkout_response.status_code,
            detail=checkout_response.json()["detail"]
        )

    # Store checkout in Redis
    checkout_id = redis_client.incr("checkout_counter")
    checkout_data = {
        "id": checkout_id,
        "type": "checkout",
        "user_id": user_id,
        "book_id": book_id
    }
    redis_client.hset(f"checkout:{checkout_id}", mapping=checkout_data)
    redis_client.lpush("checkouts", checkout_id)

    return {"message": "Book checked out successfully"}


@app.post("/checkin/{user_id}/{book_id}")
def checkin_book(user_id: int, book_id: int):
    """Function to check in book"""
    checkin_response = requests.put(
        f"{INVENTORY_SERVICE_URL}/books/{book_id}/checkin",
        params={"user_id": user_id}, timeout=10000)
    if checkin_response.status_code != 200:
        raise HTTPException(
            status_code=checkin_response.status_code,
            detail=checkin_response.json()["detail"]
        )

    # Store checkin in Redis
    checkin_id = redis_client.incr("checkout_counter")
    checkin_data = {
        "id": checkin_id,
        "type": "checkin",
        "user_id": user_id,
        "book_id": book_id
    }
    redis_client.hset(f"checkout:{checkin_id}", mapping=checkin_data)
    redis_client.lpush("checkouts", checkin_id)

    return {"message": "Book checked in successfully"}


@app.get("/checklist")
def checkin_checkout_list():
    """Function to return list of transactions"""
    checkout_ids = redis_client.lrange("checkouts", 0, -1)
    transactions = []

    for checkout_id in checkout_ids:
        transaction = redis_client.hgetall(f"checkout:{checkout_id}")
        if transaction:
            # Get book and user details
            try:
                book_response = requests.get(
                    f"{INVENTORY_SERVICE_URL}/books/{transaction['book_id']}")
                user_response = requests.get(
                    f"{USERS_SERVICE_URL}/users/{transaction['user_id']}")

                if book_response.status_code == 200 and user_response.status_code == 200:
                    book = book_response.json()
                    user = user_response.json()
                    transactions.append({
                        "type": transaction["type"],
                        "book": book["title"],
                        "user": user["name"]
                    })
            except Exception:
                continue

    return transactions
