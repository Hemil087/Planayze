"""
Chat Agent — Phase 10

Stateless agent that answers geometry questions about a floor plan.

The agent:
  1. Receives conversation history + a FloorPlanExtraction
  2. Sends messages to Gemini with geometry tool declarations
  3. Intercepts tool calls and executes them deterministically
  4. Returns the final answer + a list of tool calls made

Key constraint: geometry reasoning is never done by the LLM.
The LLM decides *which* tool to call; the tool returns the answer;
the LLM narrates it in plain English.
"""

import json
import logging

from vertexai.generative_models import (
    GenerativeModel,
    GenerationConfig,
    Content,
    Part,
    Tool,
    FunctionDeclaration,
    SafetySetting,
    HarmCategory,
    HarmBlockThreshold,
)

from app.core.gemini import _init_vertexai
from app.core.config import get_settings
from app.schemas.extraction import FloorPlanExtraction
from app.schemas.chat import ChatMessage, ChatResponse
from app.services.chat.geometry_tools import (
    TOOL_DECLARATIONS,
    TOOL_REGISTRY,
)

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a helpful floor plan assistant for apartment buyers.
You have access to geometry tools that give you factual data about the floor plan.

RULES:
1. ALWAYS use the provided tools to answer geometry questions — never guess dimensions, areas, or directions.
2. If you need to know what rooms exist, call list_rooms first.
3. Answer in plain, buyer-friendly English. No jargon.
4. If a tool returns an error (room not found), tell the user which rooms are available.
5. Be concise — 2-3 sentences max unless the user asks for detail.
6. You may call multiple tools in one turn if needed.
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

MAX_TOOL_ROUNDS = 5  # Prevent infinite tool-call loops


def _build_gemini_tools() -> list[Tool]:
    """Convert tool declarations to Gemini Tool objects."""
    func_decls = []
    for decl in TOOL_DECLARATIONS:
        func_decls.append(FunctionDeclaration(
            name=decl["name"],
            description=decl["description"],
            parameters=decl["parameters"],
        ))
    return [Tool(function_declarations=func_decls)]


def _build_chat_history(messages: list[ChatMessage]) -> list[Content]:
    """Convert ChatMessage list to Gemini Content objects."""
    history = []
    for msg in messages:
        role = "user" if msg.role.value == "user" else "model"
        history.append(Content(
            role=role,
            parts=[Part.from_text(msg.content)],
        ))
    return history


def _execute_tool_call(
    extraction: FloorPlanExtraction,
    function_name: str,
    function_args: dict,
) -> dict:
    """Execute a geometry tool deterministically."""
    tool_fn = TOOL_REGISTRY.get(function_name)
    if tool_fn is None:
        return {"error": f"Unknown tool: {function_name}"}

    # All tools take extraction as the first argument
    if function_name == "list_rooms":
        return tool_fn(extraction)
    else:
        return tool_fn(extraction, **function_args)


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

    # Build room list for system prompt context
    room_list = ", ".join(
        f"{r.name} ({r.type.value}, {r.area_sqm:.1f}sqm)"
        for r in extraction.rooms
    )

    system_prompt = _SYSTEM_PROMPT.format(room_list=room_list)

    # Build Gemini tools
    gemini_tools = _build_gemini_tools()

    # Build conversation history (all messages except the last one)
    # The last message is sent as the new user turn
    history = _build_chat_history(messages[:-1]) if len(messages) > 1 else []
    current_message = messages[-1].content

    safety_settings = [
        SafetySetting(
            category=category,
            threshold=HarmBlockThreshold.OFF,
        )
        for category in [
            HarmCategory.HARM_CATEGORY_HARASSMENT,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        ]
    ]

    generation_config = GenerationConfig(
        temperature=0.3,
        max_output_tokens=8192,
    )

    try:
        _init_vertexai()
        settings = get_settings()
        model = GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_prompt,
        )
        chat = model.start_chat(history=history)

        # Send the user's message with tools enabled
        response = chat.send_message(
            Content(role="user", parts=[Part.from_text(current_message)]),
            tools=gemini_tools,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )

        # Tool call loop — handle sequential tool calls
        for _ in range(MAX_TOOL_ROUNDS):
            # Check if the response contains function calls
            function_calls = []
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.function_call:
                            function_calls.append(part.function_call)

            if not function_calls:
                # No more tool calls — extract the text response
                break

            # Execute each function call and collect results
            tool_response_parts = []
            for fc in function_calls:
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}

                logger.info(f"Chat tool call: {fn_name}({fn_args})")
                tool_calls_made.append(fn_name)

                result = _execute_tool_call(extraction, fn_name, fn_args)

                tool_response_parts.append(
                    Part.from_function_response(
                        name=fn_name,
                        response={"result": result},
                    )
                )

            # Send tool results back to the model
            response = chat.send_message(
                Content(role="user", parts=tool_response_parts),
                tools=gemini_tools,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )

        # Extract final text response
        reply = ""
        for candidate in response.candidates:
            if candidate.content and candidate.content.parts:
                for part in candidate.content.parts:
                    if part.text:
                        reply += part.text

        reply = reply.strip()
        if not reply:
            reply = "I wasn't able to generate a response. Please try rephrasing your question."

        logger.info(
            f"Chat agent responded. Tool calls: {tool_calls_made}"
        )

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