# backend/app/schemas/chatbot.py

from pydantic import BaseModel, Field
from typing   import List, Dict, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """Single message in conversation"""
    role:      str   # "user" or "assistant"
    content:   str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    """Request body for chat endpoint"""
    message:  str             = Field(..., min_length=1, max_length=1000)
    history:  List[ChatMessage] = Field(default=[])

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is my current balance?",
                "history": []
            }
        }


class ChatResponse(BaseModel):
    """Response from AI chatbot"""
    reply:             str
    intent:            Optional[str] = None
    tokens_used:       Optional[int] = None
    model:             Optional[str] = None
    timestamp:         str

    class Config:
        json_schema_extra = {
            "example": {
                "reply":       "Your current account balance is ₹25,000.00...",
                "intent":      "balance_inquiry",
                "tokens_used": 350,
                "model":       "llama3-70b-8192",
                "timestamp":   "2024-12-15T10:30:00"
            }
        }


class ChatHistoryItem(BaseModel):
    """Stored chat history item"""
    id:          str
    user_message: str
    ai_reply:    str
    intent:      Optional[str]
    timestamp:   datetime