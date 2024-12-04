// ChatWidget.tsx
import React, { useState, useEffect, useRef } from 'react';
import './ChatWidget.css';

interface Message {
    type: 'user' | 'bot';
    content: string;
    isScheduling?: boolean;
    url?: string;
    linkText?: string;
}

interface ChatWidgetProps {
    isOpen: boolean;
    setIsOpen: (isOpen: boolean) => void;
}

const WS_URL = import.meta.env.PROD 
    ? `wss://riccoai-1.onrender.com/ws`  // Production
    : `ws://localhost:8000/ws`;          // Development

interface ThinkingDotsProps {
    className?: string;
}

const ThinkingDots: React.FC<ThinkingDotsProps> = ({ className }) => {
    return (
        <span className={`thinking-dots ${className || ''}`}>
            <span>.</span>
            <span>.</span>
            <span>.</span>
        </span>
    );
};

const ChatWidget: React.FC<ChatWidgetProps> = ({ isOpen, setIsOpen }) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState<string>('');
    const [ws, setWs] = useState<WebSocket | null>(null);
    const [sessionId, setSessionId] = useState<string>('');
    const [isConnecting, setIsConnecting] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        setSessionId(Math.random().toString(36).substring(7));
    }, []);

    const connectWebSocket = () => {
        if (isConnecting || ws) return;

        setIsConnecting(true);
        const wsUrl = `${WS_URL}/${sessionId}`;
        console.log("Connecting to WebSocket at:", wsUrl);

        try {
            const websocket = new WebSocket(wsUrl);
            
            websocket.onopen = () => {
                console.log("WebSocket connection established");
                setIsConnecting(false);
                setWs(websocket);
                setMessages([{ 
                    type: 'bot',
                    content: "Welcome to ricco.AI! I'm Ai. How can I help you today?" 
                }]);
            };

            websocket.onmessage = (event) => {
                console.log("Received message from server:", event.data);
                setMessages(prev => prev.filter(msg => msg.content !== "thinking"));
                
                try {
                    const jsonResponse = JSON.parse(event.data);
                    if (jsonResponse.type === "scheduling") {
                        setMessages(prev => [...prev, { 
                            type: 'bot', 
                            content: jsonResponse.message,
                            isScheduling: true,
                            url: jsonResponse.url,
                            linkText: jsonResponse.linkText
                        }]);
                    } else {
                        let content = event.data;
                        if (content.startsWith("Response:")) {
                            content = content.substring(9).trim();
                        }
                        setMessages(prev => [...prev, { type: 'bot', content }]);
                    }
                } catch {
                    let content = event.data;
                    if (content.startsWith("Response:")) {
                        content = content.substring(9).trim();
                    }
                    setMessages(prev => [...prev, { type: 'bot', content }]);
                }
            };

            websocket.onerror = (error) => {
                console.error("WebSocket error:", error);
                setIsConnecting(false);
            };

            websocket.onclose = () => {
                console.log("WebSocket connection closed");
                if (ws === websocket) {
                    setWs(null);
                    setIsConnecting(false);
                }
            };
        } catch (error) {
            console.error("Error creating WebSocket:", error);
            setIsConnecting(false);
        }
    };

    // Only try to connect once when the chat is opened
    useEffect(() => {
        if (sessionId && isOpen && !ws && !isConnecting) {
            connectWebSocket();
        }
        
        return () => {
            if (ws) {
                ws.close();
                setWs(null);
            }
        };
    }, [isOpen, sessionId, ws, isConnecting]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(scrollToBottom, [messages]);

    const sendMessage = () => {
        if (input.trim() && ws) {
            try {
                console.log('Attempting to send message:', input);
                ws.send(input);
                setMessages(prev => [...prev, { type: 'user', content: input }]);
                setInput('');
                
                setMessages(prev => [...prev, { 
                    type: 'bot', 
                    content: "thinking" 
                }]);
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
                            <div key={idx} className={`message ${msg.type}`}>
                                {msg.content === "thinking" ? (
                                    <ThinkingDots />
                                ) : msg.isScheduling ? (
                                    <>
                                        {msg.content}{' '}
                                        <a 
                                            href={msg.url} 
                                            target="_blank" 
                                            rel="noopener noreferrer"
                                            style={{ color: '#0066cc', textDecoration: 'underline', fontWeight: 'bold' }}
                                        >
                                            {msg.linkText}
                                        </a>
                                    </>
                                ) : (
                                    msg.content
                                )}
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