"""
Main FastAPI application module for ricco.AI chatbot.
Handles chat functionality, message processing, and response generation.
"""

from typing import Dict, List, Optional, Union
import os
import json
import re
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from langchain.schema import HumanMessage, AIMessage
from langchain_community.chat_message_histories import UpstashRedisChatMessageHistory
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone
from openai import OpenAI
import httpx
import datetime
from pydantic import BaseModel
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

# Initialize FastAPI app
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatBot:
    def __init__(self) -> None:
        """Initialize ChatBot with necessary configurations and clients."""
        # Load environment variables
        load_dotenv()
        
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Initialize conversation states
        self.conversation_states: Dict = {}
        
        # Initialize Redis configuration
        self.memory_client = None
        
        # Initialize memory clients dictionary
        self.memory_clients = {}
        
        # Track message counts per session
        self.message_counts = {}

    def should_offer_consultation(self, message: str, state: dict) -> bool:
        """Check if we should offer a consultation based on user's message and context."""
        # Only suggest consultation after we understand their needs
        interaction_count = state.get('interaction_count', 0)
        if interaction_count < 3:
            return False
        
        consultation_triggers = [
            # Direct interest signals
            'interested in', 'want to know more',
            # Implementation interests
            'how can i', 'implement', 'use ai', 'integrate',
            # Business needs
            'my business', 'our company', 'we need', 'looking for',
            # Specific inquiries about solutions
            'how does it work', 'can you help', 'what would you recommend'
        ]
        
        # Check if we've gathered enough context
        has_business_context = state.get('business_need') is not None
        has_shown_interest = state.get('interest_area') is not None
        
        if has_business_context and has_shown_interest:
            if any(trigger in message.lower() for trigger in consultation_triggers):
                return True
            
        # Check conversation context
        if state.get('last_topic') in ['business_inquiry', 'service_interest', 'implementation']:
            return True
        
        return False

    async def process_message(self, message: str, session_id: str) -> str:
        try:
            print(f"\n[Process] Processing message for session: {session_id}")
            
            # Get history for context
            history = await self.get_chat_history(session_id)
            
            current_message = message.lower()
            
            # First, check if user is directly requesting consultation/meeting
            direct_consultation_requests = [
                'book', 'schedule', 'consultation', 'meet', 'talk to someone',
                'talk with someone', 'discuss', 'appointment', 'call'
            ]
            if any(word in current_message for word in direct_consultation_requests):
                return await self.handle_scheduling(session_id)
            
            if history and len(history) > 0:
                last_bot_message = history[-1].content.lower()
                
                print(f"\n[Process] === CONSULTATION CHECK ===")
                print(f"Last bot message: '{last_bot_message}'")
                print(f"Current message: '{current_message}'")
                
                # Check if last message suggested consultation/meeting
                consultation_suggested = any(word in last_bot_message for word in [
                    'consultation', 'discuss', 'explore', 'interested', 'meeting',
                    'would you be interested', 'schedule', 'book', 'talk more'
                ])
                
                # Expanded positive responses
                positive_responses = [
                    'yes', 'yeah', 'sure', 'ok', 'okay', 'please', 
                    'absolutely', "let's do it", 'interested', 'definitely',
                    'i would', 'yah', 'sounds good', 'that works', 'good idea',
                    'why not', 'go ahead', 'perfect', 'great'
                ]
                is_positive = any(word in current_message for word in positive_responses)
                
                if consultation_suggested and is_positive:
                    return await self.handle_scheduling(session_id)

                # Check for implementation or specific solution questions
                implementation_triggers = [
                    'how can i', 'how do i', 'implement', 'integrate', 'setup',
                    'configure', 'install', 'use', 'start', 'begin with'
                ]
                if any(trigger in current_message for trigger in implementation_triggers):
                    return "I'd be happy to discuss implementation details. Would you like to schedule a consultation to explore this further?"

                if is_acknowledgment(message):
                    return await self.handle_acknowledgment(session_id)

            # Get or initialize state
            state = self.conversation_states.get(session_id, {})
            
            # Increment interaction count
            state['interaction_count'] = state.get('interaction_count', 0) + 1
            self.conversation_states[session_id] = state
            
            # Check message count limit
            if session_id not in self.message_counts:
                self.message_counts[session_id] = 0
            self.message_counts[session_id] += 1
            
            if self.message_counts[session_id] > 50:
                return "I apologize, but you've reached the maximum number of messages for this session. Please schedule a consultation to discuss your needs in detail."
            
            # Get chat history first
            history = await self.get_chat_history(session_id)
            print(f"[Process] Retrieved {len(history) if history else 0} messages from history")
            
            # For first message, determine if it's a greeting or direct question
            if len(history) == 0:
                is_greeting = await self.is_greeting(message)
                
                if is_greeting:
                    response = "Hello! What would you like to know about our AI solutions for businesses?"
                else:
                    response = await self.process_direct_question(message)
                    
                await self.save_chat_history(session_id, {"role": "user", "content": message})
                await self.save_chat_history(session_id, {"role": "assistant", "content": response})
                return response
            
            # Handle "tell me about this site/company" type questions first
            if any(phrase in message.lower() for phrase in ['about this site', 'about your site', 'what is this site', 'about your company', 'tell me about']):
                response = "ricco.AI helps businesses implement AI solutions for growth and efficiency. Which area interests you: Strategy, Analytics, or Automation?"
                await self.save_chat_history(session_id, {"role": "user", "content": message})
                await self.save_chat_history(session_id, {"role": "assistant", "content": response})
                return response
            
            # Handle services inquiry first
            if any(phrase in message.lower() for phrase in ['what services', 'kind of services', 'which services']):
                response = "We offer: AI Strategy, Data Analytics, Process Automation, and Chatbot Development. Which area interests you most?"
                await self.save_chat_history(session_id, {"role": "user", "content": message})
                await self.save_chat_history(session_id, {"role": "assistant", "content": response})
                return response

            # Only offer consultation after services are explained
            if self.should_offer_consultation(message, state):
                # Check if services were explained
                if not any("services" in msg.content for msg in history):
                    response = "I'd be happy to discuss a consultation, but first let me explain our services. What specific areas of AI interest you?"
                    await self.save_chat_history(session_id, {"role": "user", "content": message})
                    await self.save_chat_history(session_id, {"role": "assistant", "content": response})
                    return response
                
                state['consultation_suggested'] = True
                self.conversation_states[session_id] = state
                return await self.handle_scheduling(session_id)
            
            # Move the relevance check after acknowledgment handling
            relevance_check = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system", 
                    "content": """You are an AI relevance filter for an AI consultancy business.
                    
                    ALWAYS Answer Y for:
                    1. ANY acknowledgments (ok, sure, yes, thanks, etc.)
                    2. ANY follow-up responses
                    3. ANY business-related questions
                    4. Learning/education/skills
                    5. Tools/software/technology
                    6. Efficiency/productivity
                    7. Business processes
                    8. Communication methods
                    9. Data/information handling
                    10. Automation possibilities
                    11. Professional capabilities
                    12. Improvement methods
                    13. Language/writing/content
                    14. Research/analysis
                    15. Decision-making
                    16. Planning/organization
                    17. Market trends
                    18. Business legal matters
                    19. Business finance
                    20. Industry regulations
                    21. Competitive analysis
                    22. Customer service
                    23. Marketing strategies
                    24. Data security
                    25. Workflow optimization
                    26. Quality control
                    27. Resource management
                    28. Performance tracking
                    29. Forecasting/prediction
                    30. Documentation
                    31. Training methods
                    32. Collaboration
                    33. Project management
                    34. Risk assessment
                    
                    ALSO ALWAYS Answer Y for:
                    - ANY general conversation or small talk
                    - ANY greetings or farewells
                    - ANY questions or statements (unless explicitly irrelevant)
                    - ANY acknowledgments or responses
                    - ANY follow-up messages
                    - ANY expressions of interest or curiosity
                    - Questions showing general curiosity
                    - Questions that mention specific tools or processes
                    - Questions about capabilities or possibilities
                    - Questions about how things work
                    - Follow-up questions of any kind
                    - Acknowledgments or responses
                    - Questions that could indirectly relate to business solutions
                    - Common expressions (including mild expletives)
                    
                    Answer N ONLY for:
                    - Explicit gambling/betting questions
                    - Personal medical advice
                    - Personal dating/relationship advice
                    - Personal emergency situations
                    - Clearly hostile content (not including mild expletives)
                    - Questions about restaurants/food recommendations
                    - Questions about travel/tourism
                    - Questions about entertainment/movies/TV
                    - Personal shopping advice
                    - Sports-related questions
                    - Weather-related questions
                    - Questions about personal recommendations
                    
                    Special handling (Answer Y and pivot to AI solutions) for:
                    - Business legal analysis
                    - Financial modeling
                    - Market research
                    - Document processing
                    - Customer feedback
                    - Trend prediction
                    - Risk assessment
                    - Compliance
                    - Data organization
                    - Research assistance
                    
                    IMPORTANT GUIDELINES:
                    1. When in doubt, ALWAYS answer Y
                    2. ANY follow-up question gets Y
                    3. ANY acknowledgment gets Y
                    4. ANY question showing curiosity gets Y
                    5. ANY question that could POSSIBLY lead to business discussion gets Y
                    6. General conversation should ALWAYS get Y
                    
                    The goal is to maintain conversation flow and find business opportunities.
                    Err on the side of inclusion rather than exclusion.
                    Respond with single character: Y/N"""
                }, {
                    "role": "user",
                    "content": message
                }],
                temperature=0,
                max_tokens=1
            )

            is_relevant = relevance_check.choices[0].message.content.strip().upper() == 'Y'
            
            if not is_relevant:
                return "I specialize in AI solutions for businesses. What challenges is your business facing?"
            else:
                # Check if user has already booked
                if state.get('booking_completed'):
                    if any(word in message.lower() for word in ['book', 'schedule', 'consultation']):
                        return "I see you've already booked a consultation! Our team will be in touch soon. Is there anything else you'd like to know about our services?"
                
                # Check for booking-related messages
                if any(word in message.lower() for word in ['booked', 'scheduled', 'made an appointment']):
                    state['booking_completed'] = True
                    self.conversation_states[session_id] = state
                    response = "Excellent! We look forward to speaking with you. In the meantime, feel free to ask any other questions you might have."
                
                # Check for consultation interest
                elif self.should_offer_consultation(message, state):
                    state['consultation_suggested'] = True
                    self.conversation_states[session_id] = state
                    # Call Make.com webhook instead of direct Calendly
                    return await self.handle_scheduling(session_id)
                
                # Handle explicit booking requests
                elif any(word in message.lower() for word in ['book', 'schedule', 'consultation', 'meet']):
                    response = await self.handle_scheduling(session_id)
                else:
                    # Get LLM response using chat history context
                    response = await self.get_llm_response(message, session_id)
            
            # Save both the user message and response to history
            await self.save_chat_history(session_id, {
                "role": "user",
                "content": message
            })
            await self.save_chat_history(session_id, {
                "role": "assistant",
                "content": response
            })

            return response

        except Exception as e:
            print(f"[Process] Error processing message: {str(e)}")
            traceback.print_exc()
            return "I apologize, but I'm having trouble processing your message. Please try again."

    async def get_memory_client(self, session_id: str) -> UpstashRedisChatMessageHistory:
        """Get or create a Redis client for the session."""
        try:
            if session_id not in self.memory_clients:
                print("\n" + "="*50)
                print(f"🔵 [REDIS] Creating new memory client for session: {session_id}")
                
                if not self.redis_url or not self.redis_token:
                    print("❌ [REDIS] Missing configuration!")
                    raise ValueError("Redis URL and token must be configured")
                
                self.memory_clients[session_id] = UpstashRedisChatMessageHistory(
                    url=self.redis_url,
                    token=self.redis_token,
                    session_id=f"chat:{session_id}",
                    ttl=3600
                )
                print(f"✅ [REDIS] Successfully created memory client for: {session_id}")
                print("="*50 + "\n")
                
            return self.memory_clients[session_id]
            
        except Exception as e:
            print(f"\n❌ [REDIS] Error creating memory client: {str(e)}")
            traceback.print_exc()
            raise

    async def save_chat_history(self, session_id: str, message: dict) -> None:
        """Save chat message to history."""
        try:
            print(f"\n[Redis] Attempting to save message for session: {session_id}")
            # Initialize memory client if not exists
            if not self.memory_client:
                print(f"[Redis] Initializing new memory client for session: {session_id}")
                self.memory_client = UpstashRedisChatMessageHistory(
                    url=os.getenv("UPSTASH_REDIS_URL"),
                    token=os.getenv("UPSTASH_REDIS_TOKEN"),
                    session_id=session_id,
                    ttl=86400
                )
            
            # Convert dict to ChatMessage format
            if message["role"] == "user":
                chat_message = HumanMessage(content=message["content"])
            else:
                chat_message = AIMessage(content=message["content"])
            
            self.memory_client.add_message(chat_message)
            print(f"[Redis] Successfully saved message: {message['content'][:50]}...")
            
        except Exception as e:
            print(f"[Redis] Error saving to Upstash: {str(e)}")
            traceback.print_exc()

    async def get_chat_history(self, session_id: str) -> List:
        """Retrieve chat history for the session."""
        try:
            print(f"\n[Redis] Attempting to get history for session: {session_id}")
            # Initialize memory client if not exists
            if not self.memory_client:
                print(f"[Redis] Initializing new memory client for session: {session_id}")
                self.memory_client = UpstashRedisChatMessageHistory(
                    url=os.getenv("UPSTASH_REDIS_URL"),
                    token=os.getenv("UPSTASH_REDIS_TOKEN"),
                    session_id=session_id,
                    ttl=86400
                )
            messages = self.memory_client.messages
            print(f"[Redis] Retrieved {len(messages)} messages from history")
            return messages
            
        except Exception as e:
            print(f"[Redis] Error getting chat history: {str(e)}")
            traceback.print_exc()
            return []

    async def get_llm_response(self, prompt: str, session_id: str) -> str:
        try:
            messages = [{
                "role": "system", 
                "content": """You are an AI assistant for ricco.AI, an AI consultancy company. Your primary goal is to qualify leads and guide them towards scheduling a consultation.

                CORE PRINCIPLES:
                1. Your main objective is lead generation - every conversation should aim to schedule a consultation
                2. Never provide detailed solutions or technical advice - instead, suggest a consultation
                3. Never recommend third-party products or services
                4. Keep responses focused on ricco.AI's services and expertise
                5. Always guide conversations toward business value and ROI
                
                CONVERSATION STRATEGY:
                1. First, identify visitor's business challenges and needs
                2. Demonstrate understanding of their industry/problem, and ask relevant questions about their needs
                3. Hint at possible solutions without giving specifics
                4. Suggest a consultation after understanding their needs
                
                RESPONSE RULES:
                1. Keep responses clear and concise (2-3 sentences maximum)
                2. Focus on business outcomes, not technical details
                3. Never provide implementation advice
                4. Always tie responses back to ricco.AI's services
                5. Look for opportunities to suggest a consultation
                6. Only suggest consultation after understanding their needs
                
                WHEN TO SUGGEST CONSULTATION:
                - After understanding their specific business needs
                - When they ask about implementation details
                - When they show clear interest in specific solutions
                - When they mention urgent business challenges
                - When they ask about costs or timelines
                
                Remember: Build understanding first, then guide toward consultation."""
            }]

            # Add conversation history context
            history = await self.get_chat_history(session_id)
            if history:
                for msg in history[-3:]:  # Last 3 messages for context
                    messages.append({
                        "role": "user" if msg.type == "human" else "assistant",
                        "content": msg.content
                    })

            # Add current prompt
            messages.append({"role": "user", "content": prompt})

            completion = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.7,
                max_tokens=100
            )

            response = completion.choices[0].message.content.strip()
            return response

        except Exception as e:
            print(f"Error in get_llm_response: {str(e)}")
            return "I apologize, but I'm having trouble. Could you tell me more about what you're looking to achieve?"

    def get_booking_link_response(self) -> str:
        """Generate booking link response when appropriate."""
        return json.dumps({
            "type": "scheduling",
            "message": "Great! Here's the link to schedule your consultation:",
            "url": "https://calendly.com/d/cqvb-cvn-6gc/15-minute-meeting",
            "linkText": "Book your consultation"
        })

    def handle_booking_status(self, message: str, session_id: str) -> Optional[str]:
        """Handle booking-related messages."""
        state = self.conversation_states.get(session_id, {})
        
        # Check if booking was already completed
        if state.get('booking_completed'):
            return None  # Don't send booking responses if already booked
        
        # Check if user just completed booking
        if any(word in message.lower() for word in ['booked', 'scheduled', 'made an appointment', 'book it', 'booked it']):
            state['booking_completed'] = True
            self.conversation_states[session_id] = state
            return "Excellent! We look forward to speaking with you. In the meantime, feel free to ask any other questions you might have."
            
        # Only offer booking if not already booked
        if any(word in message.lower() for word in ['yes', 'yeah', 'sure', 'ok']) and state.get('consultation_suggested'):
            return self.get_booking_link_response()
            
        return None

    async def handle_acknowledgment(self, session_id: str) -> str:
        """Handle user acknowledgments based on conversation context."""
        try:
            history = await self.get_chat_history(session_id)
            
            if not history:
                return "What specific business challenges would you like to address?"
            
            last_bot_message = history[-1].content.lower()
            current_state = self.conversation_states.get(session_id, {})
            
            # First priority: Check for consultation suggestion response
            if any(word in last_bot_message for word in [
                'consultation', 'discuss', 'explore', 'interested', 'meeting',
                'would you be interested', 'schedule', 'book', 'talk more'
            ]):
                return await self.handle_scheduling(session_id)
            
            # If they've shown interest in specific solutions
            if any(topic in last_bot_message for topic in ['analytics', 'automation', 'strategy', 'implementation']):
                return await self.handle_scheduling(session_id)
            
            # If they've expressed interest in data analytics
            if 'data analytics' in last_bot_message or 'analytics' in last_bot_message:
                return "Would you like to discuss how our data analytics solutions can improve your decision-making process?"
            
            # If they've expressed interest in AI strategy
            if 'strategy' in last_bot_message or 'ai strategy' in last_bot_message:
                return "Would you like to explore how an AI strategy could benefit your business?"
            
            # If they've expressed interest in automation
            if 'automation' in last_bot_message or 'process' in last_bot_message:
                return "Would you like to discuss which processes in your business we could help automate?"
            
            # Default response
            return "Could you tell me more about your specific business needs?"
            
        except Exception as e:
            print(f"Error in handle_acknowledgment: {str(e)}")
            return "What specific challenges would you like to address?"

    async def handle_scheduling(self, session_id: str) -> str:
        """Handle scheduling request through Make.com webhook."""
        try:
            print(f"[Make.com] Sending scheduling request for session: {session_id}")
            
            # Get conversation history for context
            history = await self.get_chat_history(session_id)
            recent_messages = [msg.content for msg in history[-3:]]  # Last 3 messages
            
            # Prepare payload for Make.com
            payload = {
                "session_id": session_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "action": "create_scheduling_link",
                "conversation_context": recent_messages
            }
            
            # Send request to your specific Make.com webhook
            async with httpx.AsyncClient() as client:
                webhook_url = "https://hook.us1.make.com/ke4n6kdh0kxwwrljdq9jesotouirragi"
                response = await client.post(
                    webhook_url,
                    json=payload,
                    timeout=10.0
                )
                
                print(f"[Make.com] Response status: {response.status_code}")
                print(f"[Make.com] Response body: {response.text}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        booking_url = data.get("booking_url")
                        if booking_url:
                            return json.dumps({
                                "type": "scheduling",
                                "message": "I understand you're interested in our services. Here's a link to schedule a consultation:",
                                "url": booking_url,
                                "linkText": "Book your consultation"
                            })
                    except Exception as e:
                        print(f"[Make.com] Error parsing response: {str(e)}")
                
                # Fallback to direct Calendly link
                print("[Make.com] Falling back to direct Calendly link")
                return self.get_booking_link_response()
                
        except Exception as e:
            print(f"[Make.com] Error: {str(e)}")
            return self.get_booking_link_response()

    async def is_greeting(self, message: str) -> bool:
        """Use LLM to determine if a message is a greeting."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": """Determine if the given message is primarily a greeting/introduction or a direct question/request.

                    Examples of greetings:
                    - Hi, hello, hey
                    - Good morning/afternoon/evening
                    - Hi there, how are you
                    - Hello AI
                    
                    Respond with a single character:
                    Y - if it's primarily a greeting
                    N - if it's a direct question/request"""
                }, {
                    "role": "user",
                    "content": message
                }],
                temperature=0,
                max_tokens=1
            )
            
            return response.choices[0].message.content.strip().upper() == 'Y'
            
        except Exception as e:
            print(f"Error in greeting detection: {str(e)}")
            # Fallback to basic check
            greetings = {'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening'}
            return any(message.lower().startswith(g) for g in greetings)

    async def process_direct_question(self, message: str) -> str:
        """Handle direct questions with lead generation focus."""
        # Handle services inquiry
        if any(phrase in message.lower() for phrase in ['what services', 'kind of services', 'which services']):
            return """We specialize in: AI Strategy Development, AI-optimized Research & Data Analytics, and Business Process Automation

Which of these areas would benefit your business most? """
            
        # Handle "about this site" questions
        if any(phrase in message.lower() for phrase in ['about this site', 'about your site', 'what is this site']):
            return "ricco.AI is a leading AI consultancy that helps businesses achieve significant growth through strategic AI implementation. Would you like to learn how we could help your business?"
            
        # For other questions, focus on scheduling a consultation
        return await self.get_llm_response(message, None)

# Initialize chatbot instance
chatbot = ChatBot()

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for chat functionality."""
    print(f"New WebSocket connection attempt from session: {session_id}")
    try:
        await websocket.accept()
        print(f"WebSocket connection accepted for session: {session_id}")
        
        while True:
            try:
                print(f"[{session_id}] Waiting for message...")
                message = await websocket.receive_text()
                print(f"[{session_id}] Received message: {message}")
                
                # Handle booking status first
                booking_response = chatbot.handle_booking_status(message, session_id)
                if booking_response:
                    print(f"[{session_id}] Sending booking response: {booking_response}")
                    await websocket.send_text(booking_response)
                    continue

                # Handle acknowledgments
                if is_acknowledgment(message):
                    ack_response = await chatbot.handle_acknowledgment(session_id)
                    print(f"[{session_id}] Sending acknowledgment response: {ack_response}")
                    await websocket.send_text(ack_response)
                    continue

                # Process regular message
                response = await chatbot.process_message(message, session_id)
                print(f"[{session_id}] Sending response: {response}")
                await websocket.send_text(response)
                print(f"[{session_id}] Response sent successfully")
                
            except WebSocketDisconnect:
                print(f"[{session_id}] WebSocket disconnected")
                break
            except Exception as e:
                print(f"[{session_id}] Error: {str(e)}")
                traceback.print_exc()
                try:
                    await websocket.send_text("I apologize, but I'm having trouble processing your message. Could you please rephrase that?")
                except:
                    print(f"[{session_id}] Could not send error message to client")
                break
    except Exception as e:
        print(f"Error accepting WebSocket connection: {str(e)}")
        traceback.print_exc()

def is_acknowledgment(message: str) -> bool:
    """Use LLM to intelligently determine if a message is an acknowledgment."""
    try:
        response = chatbot.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": """Determine if the given message is an acknowledgment or affirmative response.

                Examples of acknowledgments include (but are not limited to):
                - Simple acknowledgments (ok, thanks, sure)
                - Affirmative responses (yes, yeah, let's do it)
                - Polite agreements (that would be great, sounds good)
                - Enthusiastic acceptances (oh yes please, absolutely)
                - Context-dependent responses that indicate agreement
                
                Respond with a single character:
                Y - if the message is an acknowledgment/affirmative
                N - if it's not an acknowledgment"""
            }, {
                "role": "user",
                "content": message
            }],
            temperature=0,
            max_tokens=1
        )
        
        return response.choices[0].message.content.strip().upper() == 'Y'
        
    except Exception as e:
        print(f"Error in acknowledgment detection: {str(e)}")
        # Fallback to basic check
        basic_acknowledgments = {'yes', 'yeah', 'sure', 'ok', 'please', 'yep', 'yah'}
        return any(word in message.lower().split() for word in basic_acknowledgments)

def is_booking_related(message: str) -> bool:
    """Check if message is related to booking/scheduling."""
    booking_terms = {
        'book', 'schedule', 'appointment', 'meeting', 'consultation',
        'booked', 'scheduled', 'set up', 'made', 'arrange', 'meet'
    }
    return any(term in message.lower() for term in booking_terms)

def is_consultation_acceptance(message: str, state: dict) -> bool:
    """Check if message is accepting a consultation offer."""
    if not state.get('consultation_suggested'):
        return False
        
    acceptance_terms = {'yes', 'yeah', 'yah', 'sure', 'ok', 'okay', 'lets do it', 'interested'}
    return any(term in message.lower() for term in acceptance_terms)

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

@app.post("/contact")
async def handle_contact(contact: ContactForm):
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = os.getenv("EMAIL_ADDRESS")  # robotricco@gmail.com
        msg['To'] = os.getenv("RECEIVER_EMAIL")   # x@ricco.ai
        msg['Subject'] = f"New Contact Form Submission from {contact.name}"

        body = f"""
        New contact form submission:
        
        Name: {contact.name}
        Email: {contact.email}
        Message: {contact.message}
        """

        msg.attach(MIMEText(body, 'plain'))

        # Create SMTP session
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(
                os.getenv("EMAIL_ADDRESS"),
                os.getenv("EMAIL_PASSWORD")  # ulkebbqzmwktworc
            )
            text = msg.as_string()
            server.send_message(msg)

        print(f"Received and sent contact form: {contact}")
        return {"status": "success"}
    except Exception as e:
        print(f"Error processing contact form: {e}")
        return {"status": "error", "message": str(e)}

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)