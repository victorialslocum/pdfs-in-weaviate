import os
import weaviate
from weaviate.classes.init import Auth
from weaviate.agents.query import QueryAgent
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from weaviate.agents.classes import ChatMessage

load_dotenv()

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for debugging
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Best practice: store your credentials in environment variables
weaviate_url = os.environ["WEAVIATE_URL"]
weaviate_api_key = os.environ["WEAVIATE_API_KEY"]

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=weaviate_url,
    auth_credentials=Auth.api_key(weaviate_api_key),
)

qa = QueryAgent(
    client=client, collections=["ArxivPDFs", "PDFchunks1"]
)


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]

class Source(BaseModel):
    object_id: str
    collection: str

@app.get("/")
def read_root():
    return {"message": "Weaviate QA Backend is running"}

@app.post("/api/chat")
def chat_endpoint(request: ChatRequest):
    # Convert request messages to Weaviate ChatMessage objects
    conversation = []
    for msg in request.messages:
        conversation.append(ChatMessage(role=msg.role, content=msg.content))

    # The last message is the user's query, which is already in the conversation list
    # But qa.ask() expects the conversation history.
    # If we pass the whole conversation list to qa.ask(), it will use it.
    
    try:
        response = qa.ask(conversation)
        print("response: ", response)
        
        return {
            "response": response.final_answer,
            "sources": [Source(object_id=source.object_id, collection=source.collection) for source in response.sources]
        }
    except Exception as e:
        print(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sources")
def get_source_object(source: Source):
    collection = client.collections.use(source.collection)
    source_obj = collection.query.fetch_object_by_id(source.object_id)
    
    properties = source_obj.properties
    
    # If it's a chunk, fetch the parent PDF info
    if source.collection == "PDFchunks1" and "doc_id" in properties:
        try:
            pdfs_collection = client.collections.use("ArxivPDFs")
            pdf_obj = pdfs_collection.query.fetch_object_by_id(properties["doc_id"])
            # Merge PDF properties into the response, but keep chunk text distinct
            properties["pdf_title"] = pdf_obj.properties.get("title")
            properties["pdf_date"] = pdf_obj.properties.get("date")
            properties["pdf_url"] = pdf_obj.properties.get("pdf_url")
        except Exception as e:
            print(f"Error fetching parent PDF: {e}")
            
    return properties