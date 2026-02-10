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
from model.chatbot import *
from openai import OpenAI
import json 

# Load environment variables
load_dotenv()

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure OpenAI client for DeepSeek via OpenRouter
api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-large",
    api_key=api_key
)

client = openai.OpenAI(
    api_key=api_key,
)

event_metadata_vector_store = Chroma(
    collection_name="event_metadata",
    persist_directory="chroma_db",
    embedding_function=embeddings
)
num_results = 10
event_retriever = event_metadata_vector_store.as_retriever(search_kwargs={'k': num_results})
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

        # Step 1: Extract structure 
        structure_content = text_to_structure(client, user_message)
        print(structure_content)
        structure_dict = json.loads(structure_content) 
        # Step 2: RAG: 
        knowledges = ""
        #step 2.1 RAG event description 
        if structure_dict["event_description"]!= None:
            knowledge = get_knowledge(event_retriever, structure_dict["event_description"])
            # result_with_scores = event_metadata_vector_store.similarity_search_with_score(request.message, k=num_results)
            # print(result_with_scores)
            knowledges+=f"Event description:\n {knowledge}"
        print(knowledges)
        # Step 2: Extract SQL 
        assistant_content = text_to_sql(client, user_message,structure=structure_content,  knowledge=knowledges)
        
        # # Add assistant response to history
        # assistant_message = Message(role="assistant", content=assistant_content)
        # conversation_history.append(assistant_message)
        
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
