"""
Worker Node.

Executes tasks when the decision allows autonomous or tool-assisted action.
This is where the actual work gets done.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode

from app.config import get_config
from app.state.schema import ADEState, DecisionRecord
from app.state.enums import DecisionType


WORKER_SYSTEM_PROMPT = """You are a helpful AI assistant executing a task.

You have been authorized to work on this task based on a risk assessment.
Complete the task thoroughly and accurately.

Guidelines:
1. Be thorough but concise
2. Cite sources when making factual claims
3. Clearly state any assumptions
4. If you encounter uncertainty, note it explicitly
5. Never fabricate information
6. Format your response clearly

Current date: {current_date}

Authorization level: {decision_level}
"""


def worker(state: ADEState) -> dict:
    """
    Execute the task and produce work output.
    
    Pure function: takes state, returns state updates.
    """
    config = get_config()
    analysis = state["task_analysis"]
    decision = state["decision"]
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    )
    
    # Build context from previous attempts if any
    context_parts = [f"Task: {state['task_input']}\n"]
    
    if state.get("evaluation") and state["retry_count"] > 0:
        context_parts.append(
            f"\nPrevious attempt feedback: {state['evaluation'].feedback}\n"
            f"Issues to address: {', '.join(state['evaluation'].issues)}\n"
        )
    
    if state.get("human_response"):
        context_parts.append(f"\nHuman guidance: {state['human_response']}\n")
    
    system_message = WORKER_SYSTEM_PROMPT.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        decision_level=decision.value if decision else "unknown",
    )
    
    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content="".join(context_parts)),
    ]
    
    # Add conversation history if exists
    for msg in state.get("messages", []):
        messages.append(msg)
    
    response = llm.invoke(messages)
    
    # Create audit record
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="worker",
        decision=decision or DecisionType.AUTONOMOUS,
        reasoning=f"Task executed (attempt {state['retry_count'] + 1})",
    )
    
    return {
        "work_output": response.content,
        "messages": [
            HumanMessage(content=state["task_input"]),
            response,
        ],
        "decision_path": [record],
    }


def tool_worker(state: ADEState, tools: list) -> dict:
    """
    Execute the task with tool access.
    
    This variant binds tools to the LLM for tool-assisted execution.
    Preserves message history to handle multi-turn tool usage.
    """
    config = get_config()
    
    # Check if we already have messages (continuing conversation)
    existing_messages = state.get("messages", [])
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    )
    llm_with_tools = llm.bind_tools(tools)
    
    system_message = WORKER_SYSTEM_PROMPT.format(
        current_date=datetime.now().strftime("%Y-%m-%d"),
        decision_level="tools",
    ) + "\n\nYou have access to tools. Use them to get real-time information when needed. Once you have the information, provide a final answer without calling more tools."
    
    if existing_messages:
        # Continue from existing conversation (includes tool results)
        messages = [SystemMessage(content=system_message)] + list(existing_messages)
    else:
        # First call - start fresh
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=f"Task: {state['task_input']}"),
        ]
    
    response = llm_with_tools.invoke(messages)
    
    # Create audit record
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="tool_worker",
        decision=DecisionType.TOOLS,
        reasoning="Task executed with tool access",
    )
    
    # If response has content (final answer), set work_output
    work_output = response.content if response.content and not getattr(response, 'tool_calls', None) else state.get("work_output")
    
    return {
        "messages": [response],
        "work_output": work_output,
        "decision_path": [record],
    }

