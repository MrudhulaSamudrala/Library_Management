"""Script for user service"""
import os
import redis

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
    print("Make sure Redis is running in WSL and the IP address is correct.")
    print("To find your WSL IP, run 'ip addr show eth0' in WSL")
    print("To start Redis in WSL, run: sudo service redis-server start")

# Initialize Redis with some sample data if empty
if not redis_client.exists("user_counter"):
    redis_client.set("user_counter", 1)
    sample_users = [
        {
            "id": 1,
            "name": "John Doe",
            "email": "john@example.com"
        },
        {
            "id": 2,
            "name": "Jane Smith",
            "email": "jane@example.com"
        }
    ]
    for user in sample_users:
        redis_client.hset(f"user:{user['id']}", mapping=user)
        redis_client.sadd("users", user['id'])


class User(BaseModel):
    """Class for users"""
    name: str
    email: str


@app.post("/users/register")
def register_user(user: User):
    """Function to register new users"""
    user_id = int(redis_client.incr("user_counter"))
    user_data = user.dict()
    user_data["id"] = user_id

    # Store user in Redis
    redis_client.hset(f"user:{user_id}", mapping=user_data)
    redis_client.sadd("users", user_id)

    return user_data


@app.get("/users/{user_id}")
def get_user(user_id: int):
    """Function to return user details based on id"""
    user_data = redis_client.hgetall(f"user:{user_id}")
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return user_data


@app.get("/users")
def get_all_users():
    """Function to return all users"""
    user_ids = redis_client.smembers("users")
    users = []
    for user_id in user_ids:
        user_data = redis_client.hgetall(f"user:{user_id}")
        if user_data:
            users.append(user_data)
    return users
