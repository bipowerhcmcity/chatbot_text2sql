from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import openai
import os
from dotenv import load_dotenv
import json
import asyncio
from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI, OpenAIEmbeddings


# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure OpenAI client for DeepSeek via OpenRouter
api_key = ""

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=api_key
)

client = openai.OpenAI(
    api_key=api_key,
)

vector_store = Chroma(
    collection_name="event_description",
    persist_directory="chroma_db",
    embedding_function=embeddings
)
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})

# Pydantic models
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[Message] = []

class ChatResponse(BaseModel):
    response: str
    conversation_history: List[Message]

# In-memory storage for conversation (in production, use a database)
conversations: Dict[str, List[Message]] = {}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main HTML page for Yue1608 AI"""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Yue1608 AI</h1><p>Frontend files not found</p>", status_code=404)
    

from openai import OpenAI

client = OpenAI(api_key=api_key)

SYSTEM_PROMPT = """
You are a senior data analyst writing Spark SQL.

CRITICAL Spark SQL rules (must follow):
- NEVER use DISTINCT inside window functions (OVER).
- DO NOT write expressions like COUNT(DISTINCT col) OVER (...).
- If distinct counting is needed:
  - Use GROUP BY, or
  - Use a subquery / CTE to deduplicate first, then aggregate.

Aggregation rules:
- If SELECT contains aggregate functions,
  all non-aggregated columns MUST appear in GROUP BY.
- Prefer GROUP BY over window functions for counting users.

JOIN RULES:
cdp_events.page_context = item_metadata.item_code
Use this join ONLY when:
- page_context indicates item code page. 
- Query involves product attributes (brand, category, model, color, etc.)

User identity rules:
- cdp_id = universal user identifier, always present for all users.
- user_id = identified user identifier (logged-in users).
- An anonymous user is defined as a user who has a cdp_id but does not have a user_id (user_id IS NULL or blank)
- An identified user is defined as a user who has both a cdp_id and a user_id (user_id IS NOT NULL or not blank)
- When a question refers to “user” without further clarification, it should be interpreted as including both anonymous and identified users, and users must be counted using COUNT DISTINCT cdp_id.
- When a question refers to “anonymous users”, users must be counted using COUNT DISTINCT user_id.
- Users must never be counted by user_id, unless the question explicitly requests it.
- Do NOT mix cdp_id and user_id unless explicitly requested.

Query guidelines:
- Generate valid Spark SQL only.
- Return SQL only. No explanation.
- Do NOT use CTE (WITH) in SQLite
- Use inline subqueries or direct aggregation instead

Do not explain.
Do not hallucinate columns.
"""

TABLE_SCHEMA = """
Table: cdp_events
cdp_id UUID PRIMARY KEY,

user_id VARCHAR,
user_time TIMESTAMP,
date DATE,

platform VARCHAR,
referrer_url TEXT,
url TEXT,

ctx_userId UUID,
ctx_eventIndex INT,
ctx_event_name VARCHAR,
ctx_screen_location VARCHAR,
ctx_location_type VARCHAR,
ctx_location_name VARCHAR,

ctx_firstEventId UUID,
ctx_firstEventTimestamp TIMESTAMP,

ctx_sessionId UUID,
ctx_sessionIndex INT,
ctx_previousSessionId UUID,

ctx_page_context VARCHAR, eg: 00003278

ctx_value NUMERIC,
ctx_label VARCHAR,

ctx_product_id VARCHAR,
ctx_product_name VARCHAR,
ctx_order_id VARCHAR,
ctx_order_type VARCHAR,
ctx_payment_type VARCHAR,

ctx_shipping_fee NUMERIC,
ctx_discounted_value NUMERIC,

ctx_fpt_uuid UUID,

device_brand VARCHAR,
device_model VARCHAR,
device_os VARCHAR,
device_os_version VARCHAR,
device_browser VARCHAR,
viewport_size VARCHAR,

ctx_osVersion VARCHAR,
ctx_osType VARCHAR,
ctx_deviceModel VARCHAR,
ctx_deviceManufacturer VARCHAR,

Table: item_metadata

item_code VARCHAR PRIMARY KEY, eg: 00003278

ten_sp VARCHAR,             -- product name. eg: Điện thoại iPhone 6 64GB Xám MG4F2VN/A
ten_viet_tat VARCHAR,       -- short Vietnamese name eg: iPhone 6 64GB
ten_upc VARCHAR,            -- UPC eg: iPhone 6
ten_nhom VARCHAR,           -- product group eg: Apple iPhone 6-128G
ten_dong VARCHAR,           -- product line eg: iPhone 6
ten_model VARCHAR,          -- model eg: iPhone 6-64
ten_nhan VARCHAR,           -- brand eg: Apple
ten_nganh VARCHAR,          -- industry eg: Apple
ten_loai VARCHAR,           -- category eg: ĐTDĐ-Apple
mau_sac VARCHAR,            -- color eg: ['Xám']

ten_don_vi_tinh VARCHAR      -- unit name: Chiếc
"""

def get_knowledge(message):
    docs = retriever.invoke(message)
    knowledge = ""
    for doc in docs:
        knowledge += doc.page_content+"\n\n"
    return knowledge

def text_to_sql(question,knowledge, dialect="SQL"):
    prompt = f"""
    SQL Dialect: {dialect}

    Schema:
    {TABLE_SCHEMA}

    Question:
    {question}

    Knowledge:
    {knowledge}

    Return only SQL.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0
    )

    return response.choices[0].message.content


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat requests and interact with DeepSeek API"""
    try:
        # Build conversation history
        conversation_history = request.conversation_history.copy()
        
        # Add user message to history
        user_message = Message(role="user", content=request.message)
        conversation_history.append(user_message)
        
        # Extract assistant response
        knowledges = get_knowledge(request.message) 
        assistant_content = text_to_sql(user_message, knowledge=knowledges)
        
        # Add assistant response to history
        assistant_message = Message(role="assistant", content=assistant_content)
        conversation_history.append(assistant_message)
        
        return ChatResponse(
            response=assistant_content,
            conversation_history=conversation_history
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
