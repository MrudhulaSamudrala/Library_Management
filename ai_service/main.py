"""AI Agent Script"""
import os
import redis

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_together import Together
from langchain.tools import Tool
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
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
    socket_connect_timeout=5,
    retry_on_timeout=True
)

# Test Redis connection
try:
    redis_client.ping()
except redis.ConnectionError as e:
    print(f"Warning: Could not connect to Redis: {str(e)}")

# Service URLs
INVENTORY_SERVICE_URL = "http://127.0.0.1:8001"
USERS_SERVICE_URL = "http://127.0.0.1:8002"
CHECKOUT_SERVICE_URL = "http://127.0.0.1:8003"


class ChatRequest(BaseModel):
    """Chat request model"""
    message: str
    session_id: str


def get_llm():
    """Initialize and return the LLM"""
    try:
        api_key = os.getenv("TOGETHER_API_KEY")
        # print(f"Debug: API Key found: {'Yes' if api_key else 'No'}")
        if not api_key:
            raise ValueError(
                "TOGETHER_API_KEY not found in environment variables")

        # print("Debug: Initializing Together LLM...")
        llm = Together(
            model="meta-llama/Llama-3.3-70B-Instruct-Turbo-Free",
            temperature=0.7,
            max_tokens=512,
            top_p=0.7,
            top_k=50,
            repetition_penalty=1.1,
            together_api_key=api_key
        )
        # print("Debug: Together LLM initialized successfully")
        return llm
    except Exception as e:
        print(f"Debug: Error in get_llm: {str(e)}")
        raise RuntimeError(f"Failed to initialize LLM: {str(e)}")


def get_available_books(query: str) -> str:
    """Get all books from Redis"""
    try:
        # Get all book keys
        book_keys = redis_client.keys("book:*")
        books = []

        for key in book_keys:
            book_data = redis_client.hgetall(key)
            title = book_data.get("title", "Unknown Title")
            author = book_data.get("author", "Unknown Author")
            quantity = book_data.get("quantity", "0")
            books.append(f"{title} by {author} (Quantity: {quantity})")

        if not books:
            return "No books found in the system."

        return "Books in the library:\n" + "\n".join(books)
    except Exception as e:
        print(f"Error getting books: {str(e)}")
        return "Error retrieving book information."


def get_user_info(query: str) -> str:
    """Get user information from Redis"""
    try:
        # Get all user keys
        user_keys = redis_client.keys("user:*")
        user_info = []

        for key in user_keys:
            user_data = redis_client.hgetall(key)
            name = user_data.get("name", "Unknown")
            email = user_data.get("email", "No email")
            user_info.append(f"User: {name} ({email})")

        if not user_info:
            return "No users found in the system."

        return "Users in the system:\n" + "\n".join(user_info)
    except Exception as e:
        print(f"Error getting user info: {str(e)}")
        return "Error retrieving user information."


def get_checkout_info(query: str) -> str:
    """Get checkout information from Redis"""
    try:
        # Get all checkout keys
        checkout_keys = redis_client.keys("checkout:*")
        checkout_info = []

        for key in checkout_keys:
            checkout_data = redis_client.hgetall(key)
            book_id = checkout_data.get("book_id", "Unknown")
            user_id = checkout_data.get("user_id", "Unknown")
            checkout_date = checkout_data.get("checkout_date", "Unknown")
            return_date = checkout_data.get("return_date", "Not returned")

            # Get book and user details
            book_data = redis_client.hgetall(f"book:{book_id}")
            user_data = redis_client.hgetall(f"user:{user_id}")

            book_title = book_data.get("title", "Unknown Book")
            user_name = user_data.get("name", "Unknown User")

            checkout_info.append(
                f"Book: {book_title} checked out by {user_name} on {checkout_date}"
            )
            if return_date != "Not returned":
                checkout_info[-1] += f", returned on {return_date}"

        if not checkout_info:
            return "No checkouts found in the system."

        return "Checkout history:\n" + "\n".join(checkout_info)
    except Exception as e:
        print(f"Error getting checkout info: {str(e)}")
        return "Error retrieving checkout information."


# Initialize LLM
llm = get_llm()

# Define tools for the agent
tools = [
    Tool(
        name="GetAvailableBooks",
        func=get_available_books,
        description="Useful for getting information about available books in the library."
    ),
    Tool(
        name="GetUserInfo",
        func=get_user_info,
        description="Useful for getting information about users in the system."
    ),
    Tool(
        name="GetCheckoutInfo",
        func=get_checkout_info,
        description="Useful for getting information about book checkouts and returns."
    )
]

# Agent Setup
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful library assistant. Use the available tools to "
     "help users with their library needs. Always use the tools to get "
     "real data, never make assumptions or provide made-up information."),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])


@app.post("/chat")
async def chat_with_agent(request: ChatRequest):
    """Function to chat with the agent"""
    try:
        # print(f"Debug: Received chat request - Message: {request.message}")

        # First, get the relevant information using tools
        context = ""
        for tool in tools:
            try:
                result = tool.func(request.message)
                if result and "Error" not in result:
                    context += f"\n{result}"
            except Exception as tool_error:
                print(f"Debug: Tool {tool.name} error: {str(tool_error)}")

        # Format the input for the model
        if context:
            formatted_input = f"Context: {context}\n\nQuestion: {request.message}"
        else:
            formatted_input = request.message
        # print(f"Debug: Formatted input: {formatted_input}")

        # Try direct LLM call
        # print("Debug: Attempting direct LLM call")
        try:
            # Get response from LLM
            direct_response = llm.invoke(formatted_input)
            # print(f"Debug: Raw LLM response: {direct_response}")

            if not direct_response or direct_response.strip() == "":
                return {
                    "status": "error",
                    "message": "I apologize, but I couldn't generate a proper response. Please try rephrasing your question.",
                    "data": None
                }

            # Clean up the response
            cleaned_response = direct_response.strip()
            if cleaned_response.startswith("?"):
                cleaned_response = cleaned_response[1:].strip()
            if cleaned_response.startswith("Response:"):
                cleaned_response = cleaned_response[8:].strip()

            return {
                "status": "success",
                "message": "Successfully processed your request",
                "data": {
                    "response": cleaned_response,
                    "context": context.strip() if context else None
                }
            }

        except Exception as direct_error:
            print(f"Debug: Direct LLM error details: {str(direct_error)}")
            print(f"Debug: Error type: {type(direct_error)}")
            return {
                "status": "error",
                "message": "I apologize, but I encountered an error while processing your request. Please try again with a different question.",
                "data": None
            }

    except Exception as e:
        print(f"Debug: Top-level error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": f"Error processing request: {str(e)}",
                "data": None
            }
        ) from e


@app.get("/")
async def root():
    """Function to check if the server is running"""
    return {"message": "Library AI Assistant is running"}
