"""
Chat Agent — Phase 10

Stateless agent that answers geometry questions about a floor plan.

The agent:
  1. Receives conversation history + a FloorPlanExtraction
  2. Sends messages to the LLM with geometry tool declarations
  3. Intercepts tool calls and executes them deterministically
  4. Returns the final answer + a list of tool calls made

Key constraint: geometry reasoning is never done by the LLM.
The LLM decides *which* tool to call; the tool returns the answer;
the LLM narrates it in plain English.
"""

import json
import logging
import re
import time

from json_repair import repair_json
from openai import RateLimitError

from app.core.openrouter import get_openrouter_client
from app.core.config import get_settings
from app.schemas.extraction import FloorPlanExtraction
from app.schemas.chat import ChatMessage, ChatResponse
from app.services.chat.geometry_tools import (
    TOOL_DECLARATIONS,
    TOOL_REGISTRY,
)

logger = logging.getLogger(__name__)
settings = get_settings()

_SYSTEM_PROMPT = """\
You are a helpful floor plan assistant for apartment buyers.
You have access to geometry tools that give you factual data about the floor plan.

RULES:
1. ALWAYS use the provided tools to answer geometry questions — never guess dimensions, areas, or directions.
2. If you need to know what rooms exist, call list_rooms first.
3. Answer in plain, buyer-friendly English. No jargon.
4. If a tool returns an error (room not found), tell the user which rooms are available.
5. Be concise — 2-3 sentences max unless the user asks for detail.
6. For questions about multiple rooms (e.g. "which rooms get morning sun?"), call the tool for ALL relevant rooms in a single response — do not wait for results before calling the next tool.
7. ALWAYS call a tool before responding. Never ask the user for information you can look up with a tool.
8. When the user asks about furniture, use these standard Indian dimensions and call fits_furniture immediately:
   - Queen bed: 1.5m × 2.0m
   - King bed: 1.8m × 2.0m
   - Single bed: 0.9m × 2.0m
   - Double bed: 1.35m × 1.9m
   - 2-seater sofa: 1.5m × 0.9m
   - 3-seater sofa: 2.1m × 0.9m
   - Dining table (4-seater): 1.2m × 0.75m
   - Dining table (6-seater): 1.8m × 0.9m
   - Study desk: 1.2m × 0.6m
   - Wardrobe: 1.8m × 0.6m

AVAILABLE ROOMS (for reference):
{room_list}
"""

_TOOLS = [{"type": "function", "function": decl} for decl in TOOL_DECLARATIONS]

MAX_TOOL_ROUNDS = 15
MAX_RETRY_ATTEMPTS = 3


def _build_message_history(messages: list[ChatMessage]) -> list[dict]:
    """Convert ChatMessage list to OpenAI message dicts."""
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in messages
    ]


def _clean_reply(text: str) -> str:
    """Strip leaked tool call syntax the model sometimes outputs as plain text."""
    text = re.sub(r'<\|tool_call\>.*?<tool_call\|>', '', text, flags=re.DOTALL)
    text = re.sub(r'call:\w+\{.*?\}', '', text, flags=re.DOTALL)
    return text.strip()


def _safe_parse_tool_args(raw: str | None) -> dict:
    """Parse tool call arguments — uses json_repair for malformed JSON."""
    if not raw:
        return {}
    try:
        result = repair_json(raw, return_objects=True)
        return result if isinstance(result, dict) else {}
    except Exception:
        return {}


def _chat_with_retry(client, max_attempts: int = MAX_RETRY_ATTEMPTS, **kwargs):
    """
    Wrap chat completions create with 429 retry logic.
    Reads retry_after_seconds from OpenRouter metadata when available.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError as e:
            if attempt == max_attempts:
                raise
            try:
                wait = int(e.response.json()["error"]["metadata"]["retry_after_seconds"]) + 2
            except Exception:
                wait = 30
            logger.warning(
                f"Rate limited on attempt {attempt}/{max_attempts}, "
                f"waiting {wait}s before retry..."
            )
            time.sleep(wait)


def _execute_tool_call(
    extraction: FloorPlanExtraction,
    function_name: str,
    function_args: dict,
) -> dict:
    """Execute a geometry tool deterministically. Never raises — always returns a dict."""
    tool_fn = TOOL_REGISTRY.get(function_name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {function_name}"}

    logger.info(f"Tool args for {function_name}: {function_args}")

    if function_name == "list_rooms":
        return tool_fn(extraction)

    if not function_args:
        return {
            "error": (
                f"Tool '{function_name}' received empty arguments. "
                "Please call the tool again with the correct parameters."
            )
        }

    try:
        return tool_fn(extraction, **function_args)
    except TypeError as e:
        return {"error": f"Tool '{function_name}' argument error: {str(e)}"}
    except Exception as e:
        return {"error": f"Tool '{function_name}' unexpected error: {str(e)}"}


async def run_chat_agent(
    extraction: FloorPlanExtraction,
    messages: list[ChatMessage],
) -> ChatResponse:
    """
    Run the chat agent with geometry tool calling.

    Args:
        extraction:  FloorPlanExtraction loaded from DB.
        messages:    Full conversation history (user + assistant turns).

    Returns:
        ChatResponse with the agent's reply and list of tool calls made.
    """
    tool_calls_made: list[str] = []
    reply = ""

    room_list = ", ".join(
        f"{r.name} ({r.type.value}, {r.area_sqm:.1f}sqm)"
        for r in extraction.rooms
    )
    system_prompt = _SYSTEM_PROMPT.format(room_list=room_list)

    openai_messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *_build_message_history(messages),
    ]

    client = get_openrouter_client()

    try:
        for round_num in range(MAX_TOOL_ROUNDS):
            response = _chat_with_retry(
                client,
                model=settings.OPENROUTER_CHAT_MODEL,
                messages=openai_messages,
                tools=_TOOLS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=8192,
            )

            # Guard: model returned no choices (transient upstream error)
            if not response.choices:
                logger.warning(
                    f"Round {round_num + 1}: model returned empty choices — breaking"
                )
                break

            assistant_msg = response.choices[0].message

            # Append assistant turn to history so the next call has full context
            assistant_dict: dict = {
                "role": "assistant",
                "content": assistant_msg.content,
            }
            if assistant_msg.tool_calls:
                assistant_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in assistant_msg.tool_calls
                ]
            openai_messages.append(assistant_dict)

            # No tool calls — model produced its final text answer
            if not assistant_msg.tool_calls:
                reply = _clean_reply(assistant_msg.content or "")
                logger.info(f"Final answer on round {round_num + 1}")
                break

            # Execute each tool call and append results
            for tc in assistant_msg.tool_calls:
                fn_name = tc.function.name
                fn_args = _safe_parse_tool_args(tc.function.arguments)

                logger.info(f"Chat tool call [{round_num + 1}]: {fn_name}({fn_args})")
                tool_calls_made.append(fn_name)

                result = _execute_tool_call(extraction, fn_name, fn_args)

                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result),
                })

        # Recovery: rounds exhausted or empty choices — force a text reply
        # by removing tools so the model can't loop further
        if not reply:
            logger.warning(
                "No reply after tool loop — making recovery call without tools"
            )
            openai_messages.append({
                "role": "user",
                "content": (
                    "Based on the tool results above, summarise the answer "
                    "in plain English. Do not call any tools."
                ),
            })
            recovery = _chat_with_retry(
                client,
                model=settings.OPENROUTER_CHAT_MODEL,
                messages=openai_messages,
                temperature=0.3,
                max_tokens=512,
            )
            if recovery.choices:
                reply = _clean_reply(recovery.choices[0].message.content or "")

        if not reply:
            reply = "I wasn't able to generate a response. Please try rephrasing your question."

        logger.info(f"Chat agent done. Tool calls made: {tool_calls_made}")

        return ChatResponse(
            reply=reply,
            tool_calls_made=tool_calls_made,
        )

    except Exception as e:
        logger.error(f"Chat agent error: {e}", exc_info=True)
        return ChatResponse(
            reply=f"Sorry, I encountered an error processing your question: {str(e)}",
            tool_calls_made=tool_calls_made,
        )