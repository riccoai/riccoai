# main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import httpx
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
import traceback
import os
import json
from typing import List, Dict
import datetime
from tiktoken import encoding_for_model

# Langchain imports
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import UpstashRedisChatMessageHistory
from langchain_community.document_loaders import TextLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from openai import OpenAI

# Move these to the top of the file, before creating the ChatBot instance
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')
load_dotenv(dotenv_path=env_path)

# Debug logging
print("Environment variables loaded:")
print("PINECONE_API_KEY exists:", bool(os.getenv("PINECONE_API_KEY")))
print("First few chars of PINECONE_API_KEY:", os.getenv("PINECONE_API_KEY")[:8] if os.getenv("PINECONE_API_KEY") else "None")

# First create the FastAPI app
app = FastAPI(
    title="ricco.AI API",
    description="""
    AI Consultancy API for ricco.AI.
    
    Features:
    - WebSocket chat endpoint at /ws/{session_id}
    - Health check endpoint at /health
    """,
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://riccoai-1.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Define ChatBot class first
class ChatBot:
    def __init__(self):
        # Initialize basic configurations
        self.embeddings = None
        self.vectorstore = None
        self.memory_client = None
        self.conversations = {}
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.make_webhook_url = os.getenv("MAKE_WEBHOOK_URL")
        
        # Don't initialize everything in constructor
        self.initialize_pinecone()
        
    def initialize_pinecone(self):
        # Only initialize when needed
        if not self.vectorstore:
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index = pc.Index("ricco-ai-chatbot")
            
            # Initialize embeddings with the correct model
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja",  # This is the model we used before
                model_kwargs={'device': 'cpu'}
            )

            # Initialize vectorstore with minimal settings
            self.vectorstore = PineconeVectorStore(
                index=index,
                embedding=self.embeddings,
                text_key="text",
                namespace=""
            )
        
        # Updated chat configuration to use gpt-3.5-turbo-16k
        self.chat_config = {
            "model": "gpt-3.5-turbo-16k",  # Changed to 16k version
            "temperature": 0.7,
            "top_p": 0.7,
            "max_tokens": 1000,  # Can be higher with 16k model
            "stream": True
        }

    async def get_llm_response(self, prompt: str, session_id: str) -> str:
        try:
            # Initialize memory client if not exists
            if not hasattr(self, 'memory_client') or self.memory_client is None:
                self.memory_client = UpstashRedisChatMessageHistory(
                    url=os.getenv("UPSTASH_REDIS_URL"),
                    token=os.getenv("UPSTASH_REDIS_TOKEN"),
                    session_id=session_id,
                    ttl=86400
                )
            
            # Get history from Upstash
            history = self.memory_client.messages
            
            # Initialize messages with system prompt
            messages = [{"role": "system", "content": "You are Ai, a friendly AI assistant for ricco.AI, an AI consultancy company."}]
            
            # Add only the last 5 relevant messages for context
            relevant_history = history[-5:]  # Get last 5 messages
            for msg in relevant_history:
                messages.append({
                    "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                    "content": msg.content
                })
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            # Get response from OpenAI
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo-16k",
                messages=messages,
                temperature=self.chat_config["temperature"],
                top_p=self.chat_config["top_p"],
                max_tokens=self.chat_config["max_tokens"],
                stream=self.chat_config["stream"]
            )
            
            response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    response += chunk.choices[0].delta.content
            
            # Save full history to Upstash
            self.memory_client.add_user_message(prompt)
            self.memory_client.add_ai_message(response)
            
            return response
            
        except Exception as e:
            print(f"Error in get_llm_response: {str(e)}")
            return f"Error getting LLM response: {str(e)}"

    def get_booking_link_response(self):
        """Centralized method to return booking link JSON"""
        booking_url = "https://calendly.com/d/cqvb-cvn-6gc/15-minute-meeting"
        return json.dumps({
            "type": "scheduling",
            "message": "Great! Here's the link to schedule your consultation:",
            "url": booking_url,
            "linkText": "Book your consultation now"
        })

    async def handle_scheduling(self, user_info: dict = None) -> str:
        # Send scheduling request to Make.com webhook
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "action": "schedule_meeting",
                    "timestamp": datetime.datetime.now().isoformat()
                }
        
                response = await client.post(
                    self.make_webhook_url,
                    json=payload,
                    timeout=10.0
                )
            
                print(f"Make.com response: {response.text}")  # Debug line
            
                if response.status_code == 200:
                    return self.get_booking_link_response()
                else:
                    print(f"Webhook error: Status {response.status_code}, Response: {response.text}")
                    return "I'm having trouble connecting to the scheduling system. Please try again later."
            
            except Exception as e:
                print(f"Make.com webhook error: {str(e)}")
                return "Sorry, there was an error with the scheduling system. Please try again later."

    def load_documents(self, directory: str):
        try:
            documents = []
            for file in os.listdir(directory):
                if file.endswith('.txt'):
                    loader = TextLoader(f"{directory}/{file}")
                    documents.extend(loader.load())
                elif file.endswith('.docx'):
                    loader = Docx2txtLoader(f"{directory}/{file}")
                    documents.extend(loader.load())
            
            # More memory-efficient text splitting
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,  # Reduced from 1000
                chunk_overlap=100,  # Reduced from 200
                length_function=len,
                is_separator_regex=False
            )
            texts = text_splitter.split_documents(documents)
            
            # Add documents in smaller batches
            batch_size = 100
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                self.vectorstore.add_documents(batch)
                
        except Exception as e:
            print(f"Error loading documents: {str(e)}")

    async def save_chat_history(self, session_id: str, message: dict):
        try:
            if not self.memory_client:
                self.memory_client = UpstashRedisChatMessageHistory(
                    url=os.getenv("UPSTASH_REDIS_URL"),
                    token=os.getenv("UPSTASH_REDIS_TOKEN"),
                    session_id=session_id
                )
            # Convert dict to ChatMessage format
            from langchain_core.messages import HumanMessage, AIMessage
            if message["role"] == "user":
                chat_message = HumanMessage(content=message["content"])
            else:
                chat_message = AIMessage(content=message["content"])
            self.memory_client.add_message(chat_message)
        except Exception as e:
            print(f"Error saving to Upstash: {str(e)}")

    async def get_chat_history(self, session_id: str):
        try:
            key = f"chat_history:{session_id}"
            return self.memory_client.messages
        except Exception as e:
            print(f"Error retrieving from Upstash: {str(e)}")
            return []

    async def process_message(self, message: str, session_id: str) -> str:
        try:
            # Define relevant topics and off-topic responses
            business_keywords = [
                "ai", "artificial intelligence", "business", "automation", "company", 
                "service", "consultation", "efficiency", "productivity", "data", 
                "process", "solution", "cost", "time", "revenue", "help", "improve",
                "ricco", "consulting"
            ]
            
            # Check if message is off-topic
            is_relevant = any(keyword in message.lower() for keyword in business_keywords)
            if not is_relevant and len(message.split()) > 2:  # Ignore short greetings
                return "I'm focused on helping businesses with AI solutions. How can I assist you with your business needs?"
            
            # Save incoming message to history
            await self.save_chat_history(session_id, {
                "role": "user",
                "content": message
            })

            # Check if user has already booked first
            already_booked_keywords = ["booked", "scheduled", "done", "completed"]
            if any(keyword in message.lower() for keyword in already_booked_keywords):
                response = "Great to hear you've booked a consultation! Our team will be in touch soon. Is there anything else you'd like to know about our services in the meantime?"
            # Then check if it's a new scheduling request
            elif any(word in message.lower() for word in ["schedule", "meeting", "consultation", "book", "appointment"]):
                response = await self.handle_scheduling()
            else:
                # Initialize Pinecone if not already done
                if not self.vectorstore:
                    self.initialize_pinecone()
                    
                response = await self.search_documents(message, session_id)

            # Save bot response to history
            await self.save_chat_history(session_id, {
                "role": "assistant",
                "content": response
            })

            return response
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return "I apologize, but I'm having trouble processing your message. Please try again."

    async def search_documents(self, query: str, session_id: str) -> str:
        # Initialize Upstash first
        if not self.memory_client:
            self.memory_client = UpstashRedisChatMessageHistory(
                url=os.getenv("UPSTASH_REDIS_URL"),
                token=os.getenv("UPSTASH_REDIS_TOKEN"),
                session_id=session_id
            )
        
        # Get conversation history
        recent_messages = self.memory_client.messages[-5:]  # Last 5 messages
        recent_context = "\n".join([msg.content for msg in recent_messages])
        
        # Only check scheduling keywords after company info is provided
        scheduling_keywords = ["yes", "sure", "okay", "consultation", "book", "schedule", "meet", "appointment"]
        already_booked_keywords = ["booked", "scheduled", "done", "completed"]
        
        # Check if user has already booked
        if any(keyword in query.lower() for keyword in already_booked_keywords):
            return "Great to hear you've booked a consultation! Our team will be in touch soon. Is there anything else you'd like to know about our services in the meantime?"
        
        # Get relevant documents
        docs = self.vectorstore.similarity_search(query, k=2)
        context = "\n".join([doc.page_content for doc in docs])
        
        # Different prompts based on conversation stage
        if len(recent_messages) == 0:
            prompt = """You are Ai, a friendly AI assistant for ricco.AI. 
            First message should just be welcoming and ask about their needs.
            Example: "Hello! How can we assist you with optimizing your business with AI today?"
            Keep it brief and friendly."""
        elif "tell me more about your company" in query.lower() or "what do you do" in query.lower():
            prompt = """Explain ricco.AI's services briefly:
            "ricco.AI is an AI consultancy helping businesses optimize operations through AI solutions. We focus on revenue growth, efficiency improvements, and process automation. What specific areas interest you most?" """
        elif any(keyword in query.lower() for keyword in scheduling_keywords) and len(recent_messages) > 2:
            return self.get_booking_link_response()
        else:
            prompt = f"""You are Ai, a friendly AI assistant for ricco.AI.
            Context: {context}
            Recent conversation: {recent_context}
            Question: {query}

        Instructions: 
        - NEVER end a reply without asking the user a follow-up question, such as if they are interested in a consultation
        - Don't mention scheduling or consultation until user shows clear interest
        - Keep responses brief (1-2 sentences)
        - Don't send the consultation link right away. In the message prior to presenting the link, be polite and say something like "If you'd like, we can book a consultation with one of our experts."
        - Maximum 150 characters
        - If they ask about company, explain services first
        - If they say they've booked, acknowledge and offer more info
        
        Example good follow-up responses: "That's interesting! What specific challenges are you looking to address with AI?"
        """
        
        return await self.get_llm_response(prompt, session_id)

# Then create the instance
chatbot = ChatBot()

# Now define the FastAPI routes and event handlers
@app.on_event("startup")
async def startup_event():
    try:
        # Load documents in background
        import asyncio
        asyncio.create_task(load_documents_background())
    except Exception as e:
        print(f"Startup error: {str(e)}")

async def load_documents_background():
    try:
        chatbot.load_documents("docs")
    except Exception as e:
        print(f"Document loading error: {str(e)}")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for chat functionality.
    
    Parameters:
    - session_id: Unique identifier for the chat session
    """
    print(f"New WebSocket connection attempt from session: {session_id}")
    try:
        await websocket.accept()
        print(f"WebSocket connection accepted for session: {session_id}")
        
        while True:
            try:
                # Log when waiting for a message
                print(f"[{session_id}] Waiting for message...")
                message = await websocket.receive_text()
                print(f"[{session_id}] Received message: {message}")
                
                # Process the message
                response = await chatbot.process_message(message, session_id)
                print(f"[{session_id}] Sending response: {response}")
                
                # Send response back
                await websocket.send_text(response)
                print(f"[{session_id}] Response sent successfully")
                
            except WebSocketDisconnect:
                print(f"[{session_id}] WebSocket disconnected")
                break
            except Exception as e:
                print(f"[{session_id}] Error: {str(e)}")
                traceback.print_exc()
                try:
                    await websocket.send_text("Sorry, there was an error processing your message.")
                except:
                    print(f"[{session_id}] Could not send error message to client")
                break
    except Exception as e:
        print(f"Error accepting WebSocket connection: {str(e)}")
        traceback.print_exc()

@app.get("/")
async def root():
    return {"message": "Welcome to ricco.AI API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Get the directory containing the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, '.env')

print(f"Looking for .env file at: {env_path}")
print(f"File exists: {os.path.exists(env_path)}")

# Try to read the file directly (don't log the full contents as it contains sensitive info)
try:
    with open(env_path, 'r') as f:
        first_line = f.readline().strip()
        print(f"First line starts with: {first_line[:15]}...")
except Exception as e:
    print(f"Error reading .env file: {str(e)}")

# Load the environment variables
load_dotenv(dotenv_path=env_path)

# Debug: Print environment variables (don't print full keys in production!)
print("Environment variables loaded:")
print("PINECONE_API_KEY exists:", bool(os.getenv("PINECONE_API_KEY")))
print("OPENAI_API_KEY exists:", bool(os.getenv("OPENAI_API_KEY")))
print("First few chars of PINECONE_API_KEY:", os.getenv("PINECONE_API_KEY")[:8] if os.getenv("PINECONE_API_KEY") else "None")

# Make sure the path to .env is correct
print("Current working directory:", os.getcwd())
print("Looking for .env file in:", os.path.abspath(".env"))