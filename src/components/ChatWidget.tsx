// ChatWidget.tsx
import React, { useState, useEffect, useRef } from 'react';
import './ChatWidget.css';

interface Message {
    type: 'user' | 'bot';
    content: string;
}

interface ChatWidgetProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
}

const ChatWidget: React.FC<ChatWidgetProps> = ({ isOpen, setIsOpen }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState<string>('');
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [sessionId, setSessionId] = useState<string>('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Add reconnection attempt tracking
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    const maxReconnectAttempts = 3;

    // Add connection status tracking
    const [isConnecting, setIsConnecting] = useState(false);

    useEffect(() => {
        // Generate a random session ID
        setSessionId(Math.random().toString(36).substring(7));
    }, []);

    useEffect(() => {
        // Add this initial greeting message
        setMessages([{ 
            type: 'bot', 
            content: "👋 Welcome to ricco.AI! I'm Ai. How can I help you today?" 
        }]);
    }, []); 

    const connectWebSocket = () => {
        if (isConnecting || reconnectAttempts >= maxReconnectAttempts) return;

        setIsConnecting(true);
        const websocket = new WebSocket(
            import.meta.env.DEV 
                ? `ws://localhost:8000/ws/${sessionId}`
                : `wss://riccoai-1.onrender.com/ws/${sessionId}`
        );
        
        websocket.onopen = () => {
            console.log('Connected to chat server');
            setIsConnecting(false);
            setReconnectAttempts(0);
            setMessages(prev => prev.filter(m => m.type === 'bot' && m.content.includes('Welcome')));
        };

        websocket.onmessage = (event) => {
            if (event.data === "ping") return; // Ignore ping messages
            setMessages(prev => [...prev, { type: 'bot', content: event.data }]);
        };

        websocket.onclose = () => {
            console.log('Disconnected from chat server');
            setWs(null);
            setIsConnecting(false);

            if (isOpen && reconnectAttempts < maxReconnectAttempts) {
                setReconnectAttempts(prev => prev + 1);
                setMessages(prev => [...prev, { 
                    type: 'bot', 
                    content: "Connection lost. Attempting to reconnect..." 
                }]);
                // Try to reconnect after 3 seconds
                setTimeout(() => connectWebSocket(), 3000);
            } else if (reconnectAttempts >= maxReconnectAttempts) {
                setMessages(prev => [...prev, { 
                    type: 'bot', 
                    content: "Unable to establish connection. Please refresh the page to try again." 
                }]);
            }
        };

        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
            if (!messages.some(m => m.content.includes('error connecting'))) {
                setMessages(prev => [...prev.filter(m => m.content.includes('Welcome')), { 
                    type: 'bot', 
                    content: "Connection issue detected. Attempting to reconnect..." 
                }]);
            }
        };

        setWs(websocket);
    };

    useEffect(() => {
        if (sessionId && isOpen && !ws && !isConnecting) {
            connectWebSocket();
        }

        return () => {
            if (ws) {
                ws.close();
            }
        };
    }, [sessionId, isOpen, ws, isConnecting]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const sendMessage = () => {
        if (input.trim() && ws) {
            try {
                ws.send(input);
                setMessages(prev => [...prev, { type: 'user', content: input }]);
                setInput('');
            } catch (error) {
                console.error('Error sending message:', error);
                setMessages(prev => [...prev, { 
                    type: 'bot', 
                    content: "Sorry, there was an error sending your message." 
                }]);
            }
        }
    };

    return (
        <div className="chat-widget">
            {!isOpen ? (
                <button 
                    className="chat-bubble" 
                    onClick={() => setIsOpen(true)}
                    aria-label="Open chat"
                >
                    💬
                </button>
            ) : (
                <div className="chat-window">
                    <div className="chat-header">
                        <h3>Chat with us</h3>
                        <button 
                            onClick={() => setIsOpen(false)}
                            aria-label="Close chat"
                        >×</button>
                    </div>
                    <div className="chat-messages">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`message ${msg.type}`}
                                dangerouslySetInnerHTML={{ __html: msg.content }}>
                            </div>
                        ))}
                        <div ref={messagesEndRef} />
                    </div>
                    <div className="chat-input">
                        <input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                            placeholder="Type your message..."
                            aria-label="Chat input"
                        />
                        <button 
                            onClick={sendMessage}
                            aria-label="Send message"
                        >
                            Send
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ChatWidget;