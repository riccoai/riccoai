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
app = FastAPI()

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
        
        # Updated chat configuration to use gpt-3.5-turbo
        self.chat_config = {
            "model": "gpt-3.5-turbo",  # Changed from gpt-4
            "temperature": 0.7,
            "top_p": 0.7,
            "max_tokens": 150,  # Can be higher now due to higher limits
            "stream": True
        }

    async def get_llm_response(self, prompt: str, session_id: str) -> str:
        # Get conversation history
        conversation = self.conversations.get(session_id, [])
        
        # Add current prompt to messages
        messages = [
            *[{"role": msg["role"], "content": msg["content"]} for msg in conversation],
            {"role": "user", "content": prompt}
        ]
        
        try:
            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Changed from gpt-4
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
            
            # Update conversation history
            conversation.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response}
            ])
            self.conversations[session_id] = conversation[-10:]  # Keep last 10 messages
            
            return response
        except Exception as e:
            return f"Error getting LLM response: {str(e)}"

    async def search_documents(self, query: str, session_id: str) -> str:
        docs = self.vectorstore.similarity_search(query)
        context = "\n".join([doc.page_content for doc in docs])
        
        prompt = f"""You are Ai, a friendly AI assistant for ricco.AI, an AI consultancy company. 

    Context: {context}
    Question: {query}

    Instructions: 
    - Be engaging and show genuine interest in the visitor's needs
    - After 1-2 exchanges, suggest a consultation if the user shows interest in AI services
    - Highlight ricco.AI's expertise in AI consulting and implementation
    - Suggest a consultation when user shows interest
    - Use phrases like "I'd be happy to arrange a consultation to discuss this in detail" or "Our experts can guide you through this in a consultation"
    - Keep responses brief but persuasive 
    - Maximum 3 sentences, but try to keep it 1 or 2 sentences
    - Maximum 225 characters
    - Be direct and get to the point quickly
    - If they mention any business challenges or AI interests, emphasize how a consultation could help them
    - Be natural and conversational, not pushy

    Example responses:
    - "That's a great question! Let's discuss your specific needs with one of our experts? I can help schedule a consultation."
    - "I see. I think you'd benefit from a quick chat with our AI consultants. They can provide detailed insights about [specific aspect]."

    Current conversation context: {self.conversations.get(session_id, [])}"""
        
        return await self.get_llm_response(prompt, session_id)

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
                    booking_url = "https://calendly.com/d/cqvb-cvn-6gc/15-minute-meeting"
                    # Return a JSON string that the frontend can parse
                    return json.dumps({
                        "type": "scheduling",
                        "message": "Please click here to book your consultation with us!",
                        "url": booking_url,
                        "linkText": "Click here to book your consultation"
                    })
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
            # Save incoming message to history
            await self.save_chat_history(session_id, {
                "role": "user",
                "content": message
            })

            # Check if it's a scheduling request
            if any(word in message.lower() for word in ["schedule", "meeting", "consultation", "book", "appointment"]):
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