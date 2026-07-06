from enum import Enum
from pydantic import BaseModel, Field


# -------------------------------------------------------------------
# Enums
# -------------------------------------------------------------------

class MessageRole(str, Enum):
    USER      = "user"
    ASSISTANT = "assistant"


# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single message in a conversation turn."""
    role: MessageRole = Field(..., description="Who sent this message")
    content: str      = Field(..., min_length=1, description="Message text")


class ChatRequest(BaseModel):
    """
    Incoming chat request.
    Full conversation history is sent each time — the agent is stateless.
    """
    plan_id: str                  = Field(..., description="Which floor plan to chat about")
    messages: list[ChatMessage]   = Field(..., min_length=1, description="Full conversation history")


class ChatResponse(BaseModel):
    """
    Response from the chat agent.
    tool_calls_made lets the client (and evals) verify geometry tools were used.
    """
    reply: str                    = Field(..., description="Agent's answer in plain English")
    tool_calls_made: list[str]    = Field(
        default_factory=list,
        description="Names of geometry tools called during this turn, e.g. ['fits_furniture', 'sun_exposure']",
    )