"""
Refusal Node.

Handles safe refusals when the decision is STOP.
Provides clear, helpful explanations for why the AI cannot proceed.
"""

from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.config import get_config
from app.state.schema import ADEState, DecisionRecord
from app.state.enums import DecisionType


REFUSAL_PROMPT = """You are a safety-focused AI assistant explaining why a task cannot be completed.

Your job is to provide a clear, respectful, and helpful refusal explanation.

Guidelines:
1. Be respectful and non-judgmental
2. Clearly explain the specific concerns
3. Suggest safer alternatives when possible
4. Never be preachy or condescending
5. Keep the explanation concise but complete

Structure your response as:
1. Acknowledgment of the request
2. Specific reason(s) for refusal
3. Alternative suggestions (if applicable)
4. Offer to help with related safe tasks
"""


def refusal(state: ADEState) -> dict:
    """
    Generate a clear refusal explanation.
    
    Pure function: takes state, returns state updates.
    """
    config = get_config()
    
    risk = state.get("risk_assessment")
    analysis = state.get("task_analysis")
    
    # Build context for refusal
    context_parts = [f"Task requested: {state['task_input']}\n"]
    
    if analysis:
        context_parts.append(f"Domain: {analysis.domain.value}")
        context_parts.append(f"Complexity: {analysis.complexity}")
    
    if risk:
        context_parts.append(f"\nRisk assessment:")
        context_parts.append(f"- Overall risk: {risk.overall_risk:.0%}")
        context_parts.append(f"- Reasoning: {risk.reasoning}")
        if risk.flags:
            context_parts.append(f"- Flags: {', '.join(risk.flags)}")
    
    if state.get("refusal_reason"):
        context_parts.append(f"\nAdditional context: {state['refusal_reason']}")
    
    llm = ChatOpenAI(
        model=config.model.name,
        temperature=config.model.temperature,
    )
    
    messages = [
        SystemMessage(content=REFUSAL_PROMPT),
        HumanMessage(content="\n".join(context_parts)),
    ]
    
    response = llm.invoke(messages)
    
    # Create audit record
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="refusal",
        decision=DecisionType.STOP,
        reasoning="Task refused due to safety concerns",
    )
    
    return {
        "work_output": response.content,
        "refusal_reason": state.get("refusal_reason") or "Safety thresholds exceeded",
        "decision_path": [record],
    }


def create_immediate_refusal(reason: str) -> dict:
    """
    Create an immediate refusal without LLM call.
    
    Used for hard-coded refusals (e.g., credential storage attempts).
    """
    record = DecisionRecord(
        timestamp=datetime.now(),
        node="refusal",
        decision=DecisionType.STOP,
        reasoning=reason,
    )
    
    refusal_text = f"""I cannot proceed with this request.

**Reason:** {reason}

This is a safety measure to protect you and ensure responsible AI use.

If you believe this is an error, please rephrase your request or provide more context about what you're trying to accomplish. I'm happy to help with alternative approaches that don't raise these concerns."""
    
    return {
        "decision": DecisionType.STOP,
        "work_output": refusal_text,
        "refusal_reason": reason,
        "decision_path": [record],
    }

