"""Script for inventory service"""
import os
import redis

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
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

USERS_SERVICE_URL = "http://127.0.0.1:8002"
CHECKOUT_SERVICE_URL = "http://127.0.0.1:8003"

# Initialize Redis with some sample data if empty
if not redis_client.exists("book_counter"):
    redis_client.set("book_counter", 1)
    sample_books = [
        {
            "id": 1,
            "title": "Python Programming",
            "author": "John Smith",
            "quantity": 5,
            "out": 0
        },
        {
            "id": 2,
            "title": "Data Structures",
            "author": "Jane Doe",
            "quantity": 3,
            "out": 0
        }
    ]
    for book in sample_books:
        redis_client.hset(f"book:{book['id']}", mapping=book)
        redis_client.sadd("books", book['id'])


class Book(BaseModel):
    """Class for books"""
    title: str
    author: str
    quantity: int
    out: int


@app.post("/books/")
def add_book(book: Book):
    """Function to add new books"""
    book_id = int(redis_client.incr("book_counter"))
    book_data = book.dict()
    book_data["id"] = book_id

    # Store book in Redis
    redis_client.hset(f"book:{book_id}", mapping=book_data)
    redis_client.sadd("books", book_id)

    return book_data


@app.get("/books/{book_id}")
def get_book(book_id: int):
    """Function to get books based on id"""
    book_data = redis_client.hgetall(f"book:{book_id}")
    if not book_data:
        raise HTTPException(status_code=404, detail="Book not found")
    return book_data


@app.put("/books/{book_id}/checkout")
def checkout_book(book_id: int, user_id: int):
    """Function to check out books"""
    # Validate user
    user_response = requests.get(
        f"{USERS_SERVICE_URL}/users/{user_id}", timeout=10000)
    if user_response.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found")

    # Get book data
    book_data = redis_client.hgetall(f"book:{book_id}")
    if not book_data:
        raise HTTPException(status_code=404, detail="Book not found")

    quantity = int(book_data["quantity"])
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Book out of stock")

    # Update book data
    redis_client.hincrby(f"book:{book_id}", "quantity", -1)
    redis_client.hincrby(f"book:{book_id}", "out", 1)

    updated_book = redis_client.hgetall(f"book:{book_id}")
    return {
        "message": "Book checked out",
        "remaining": updated_book["quantity"]
    }


@app.put("/books/{book_id}/checkin")
def checkin_book(book_id: int, user_id: int):
    """Function to check in books"""
    # Validate user
    user_response = requests.get(
        f"{USERS_SERVICE_URL}/users/{user_id}", timeout=10000)
    if user_response.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found")

    # Get book data
    book_data = redis_client.hgetall(f"book:{book_id}")
    if not book_data:
        raise HTTPException(status_code=404, detail="Book not found")

    out = int(book_data["out"])
    if out <= 0:
        raise HTTPException(status_code=400, detail="No such book checked out")

    # Update book data
    redis_client.hincrby(f"book:{book_id}", "quantity", 1)
    redis_client.hincrby(f"book:{book_id}", "out", -1)

    updated_book = redis_client.hgetall(f"book:{book_id}")
    return {
        "message": "Book checked in",
        "remaining": updated_book["quantity"]
    }


@app.get("/books")
def show_all_books():
    """Function to return all books"""
    book_ids = redis_client.smembers("books")
    books = []
    for book_id in book_ids:
        book_data = redis_client.hgetall(f"book:{book_id}")
        if book_data:
            books.append(book_data)
    return books


@app.get("/checkouts")
def show_checkouts():
    """Function to display transaction list"""
    checked_response = requests.get(
        f"{CHECKOUT_SERVICE_URL}/checklist", timeout=10000)
    return checked_response.json()
