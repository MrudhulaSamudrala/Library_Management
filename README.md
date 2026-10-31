# Agentic AI Library Management System

A modern library management system with AI-powered assistance.

## Key Features

- Book inventory management
- User management
- Checkout system
- AI-powered chat assistant

## Tech Stack

- **FastAPI**: Backend framework
- **Redis**: Data storage and caching
- **LangChain**: AI agent framework
- **Together AI**: LLM integration (Llama 3.3 70B)

## Setup

1. Install dependencies:
```bash
pip install fastapi redis langchain-together python-dotenv
```

2. Set up environment variables:
```bash
export TOGETHER_API_KEY=your_api_key_here
```

3. Start Redis:
```bash
sudo service redis-server start
```

4. Run the services:
```bash
uvicorn ai_service.main:app --reload --port 8000
```

## AI Assistant

The system uses an AI assistant powered by Together AI's Llama 3.3 70B model. The assistant can:
- List available books
- Show user information
- Display checkout history
- Answer questions about the library

## API Endpoints

- `POST /chat`: Chat with the AI assistant
  ```json
  {
    "message": "tell me what books are in the library",
    "session_id": "string"
  }
  ```

## Response Format

```json
{
    "status": "success",
    "message": "Successfully processed your request",
    "data": {
        "response": "and how many of each book there is\nAnswer: There are currently two books in the library. The first one is \"Python Programming\" with a quantity of four, and the second one is \"book1\" with a quantity of three.",
        "context": "Books in the library:\nPython Programming by John Smith (Quantity: 4)\nbook1 by author1 (Quantity: 3)\nUsers in the system:\nUser: John Doe (john@example.com)\nUser: Jane Smith (jane@example.com)\nCheckout history:\nBook: Python Programming checked out by John Doe on Unknown"
    }
}
``` 